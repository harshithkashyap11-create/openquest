from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from time import monotonic
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import Class, Diagnosis, Submission
from app.schemas.diagnosis import DiagnosisResult, validate_evidence_quotes
from app.services.diagnosis_provider import (
    DiagnosisProvider,
    ProviderRateLimited,
    create_diagnosis_provider,
)
from app.services.learning_service import record_evidence
from app.services.answer_evaluation import answers_match
from app.subject_taxonomy import (
    FOLLOW_UP_CODE,
    get_taxonomy,
    is_follow_up_code,
)

MAX_DIAGNOSIS_BATCH_SIZE = 20
GROUP_CONFIDENCE_THRESHOLD = 0.75


@dataclass
class DiagnosisBatchResult:
    diagnosed: int = 0
    failed: int = 0
    timed_out: int = 0
    rate_limited: int = 0
    remaining_pending: int = 0
    diagnoses: list[Diagnosis] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DiagnosisService:
    def __init__(
        self,
        db: Session,
        provider: DiagnosisProvider | None = None,
        *,
        batch_timeout_seconds: float | None = None,
    ) -> None:
        self.db = db
        self.provider = provider or create_diagnosis_provider(get_settings())
        settings = get_settings()
        self.batch_timeout_seconds = (
            settings.ai_batch_timeout_seconds
            if batch_timeout_seconds is None
            else batch_timeout_seconds
        )

    def diagnose_class(
        self, class_id: UUID, *, limit: int = MAX_DIAGNOSIS_BATCH_SIZE
    ) -> DiagnosisBatchResult:
        if not 1 <= limit <= MAX_DIAGNOSIS_BATCH_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_DIAGNOSIS_BATCH_SIZE}")
        if self.db.get(Class, class_id) is None:
            raise LookupError("Class not found")

        pending_statement = (
            select(Submission)
            .join(Submission.student)
            .where(Submission.student.has(class_id=class_id))
            .options(
                joinedload(Submission.question),
                joinedload(Submission.student),
            )
            .where(
                ~select(Diagnosis.id)
                .where(Diagnosis.submission_id == Submission.id)
                .exists()
            )
            .order_by(Submission.submitted_at, Submission.id)
            .limit(limit)
        )
        submissions = list(self.db.scalars(pending_statement).unique())
        result = DiagnosisBatchResult()
        failure_events = []
        if not submissions:
            return result

        executor = ThreadPoolExecutor(max_workers=min(5, len(submissions)))
        futures = {
            executor.submit(
                self.provider.diagnose,
                subject=submission.question.subject,
                topic=submission.question.topic,
                question=submission.question.question_text,
                answer=submission.answer,
                explanation=submission.explanation,
                correct_answer=submission.question.correct_answer,
                expected_approach=submission.question.explanation_expected,
            ): submission
            for submission in submissions
        }
        deadline = monotonic() + self.batch_timeout_seconds
        try:
            pending = set(futures)
            while pending and monotonic() < deadline:
                done, pending = wait(
                    pending,
                    timeout=max(0, deadline - monotonic()),
                    return_when=FIRST_COMPLETED,
                )
                for future in done:
                    submission = futures[future]
                    try:
                        diagnosis = self._validated_diagnosis(
                            submission, future.result()
                        )
                    except Exception as error:
                        result.failed += 1
                        if isinstance(error, ProviderRateLimited):
                            result.rate_limited += 1
                        result.errors.append(
                            f"{submission.id}: {type(error).__name__}: diagnosis unavailable; saved response can be retried"
                        )
                        failure_events.append((submission, type(error).__name__))
                        continue
                    result.diagnoses.append(diagnosis)

            if pending:
                result.timed_out = len(pending)
                result.errors.extend(
                    f"{futures[future].id}: diagnosis batch timed out"
                    for future in pending
                )
                for future in pending:
                    failure_events.append((futures[future], "BatchTimeout"))
                    future.cancel()
                result.failed += len(pending)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # Persist failures only after the bounded provider wait ends. Do not
        # hold a SQLite write transaction while another model call is pending.
        for submission, error_type in failure_events:
            record_evidence(self.db, submission.student, submission.question.subject,
                submission.question.topic, "diagnosis_failure", f"diagnosis-failure:{uuid4()}", {
                    "submission_id": str(submission.id), "error_type": error_type,
                    "retryable": True, "provider": self.provider.name})

        if result.diagnoses:
            self.db.add_all(result.diagnoses)
            self.db.flush()
            for diagnosis in result.diagnoses:
                submission = self.db.get(Submission, diagnosis.submission_id)
                record_evidence(self.db, submission.student, submission.question.subject,
                    submission.question.topic, "diagnosis", f"diagnosis-submission:{submission.id}", {
                        "observation_id": f"diagnosis:{diagnosis.id}",
                        "diagnosis_id": str(diagnosis.id), "question_id": str(submission.question_id),
                        "attempt": f"baseline:{submission.attempt_no}",
                        "code": diagnosis.misconception_code,
                        "correct": answers_match(submission.answer, submission.question.correct_answer,
                            question_text=submission.question.question_text),
                        "uncertain": diagnosis.status == "needs_followup",
                        "provider": diagnosis.provider, "model": diagnosis.model_version,
                        "evidence": diagnosis.evidence,
                        "confidence_note": "Uncalibrated provider/rule score; not a probability."})
        if result.diagnoses or result.failed:
            self.db.commit()
        result.diagnosed = len(result.diagnoses)
        result.remaining_pending = self.db.scalar(
            select(func.count(Submission.id))
            .join(Submission.student)
            .where(Submission.student.has(class_id=class_id))
            .where(
                ~select(Diagnosis.id)
                .where(Diagnosis.submission_id == Submission.id)
                .exists()
            )
        ) or 0
        return result

    def _validated_diagnosis(
        self, submission: Submission, response: DiagnosisResult
    ) -> Diagnosis:
        response = DiagnosisResult.model_validate(response)
        validate_evidence_quotes(response, submission.answer, submission.explanation)
        taxonomy = get_taxonomy(
            submission.question.subject, submission.question.topic
        )
        valid_codes = {item.code for item in taxonomy} | {
            "CORRECT",
            "M06"
            if (submission.question.subject, submission.question.topic)
            == ("Mathematics", "Fractions")
            else FOLLOW_UP_CODE,
        }
        if response.misconception_code not in valid_codes:
            raise ValueError(
                "Diagnosis code does not belong to the question subject and topic"
            )
        needs_followup = (
            is_follow_up_code(response.misconception_code)
            or response.confidence < GROUP_CONFIDENCE_THRESHOLD
            or response.needs_followup
        )
        followup_question = response.followup_question
        if needs_followup and not followup_question:
            followup_question = (
                "Can you explain how you decided on your answer?"
            )
        status = "needs_followup" if needs_followup else "provisional"
        return Diagnosis(
            submission_id=submission.id,
            misconception_code=response.misconception_code,
            confidence=response.confidence,
            evidence=response.evidence,
            misconception_description=response.misconception_description
            or next(
                (
                    item.description
                    for item in taxonomy
                    if item.code == response.misconception_code
                ),
                "",
            ),
            misunderstanding_explanation=response.misunderstanding_explanation,
            suggested_intervention=response.suggested_intervention,
            followup_question=followup_question,
            provider=self.provider.name,
            status=status,
            model_version=response.model_version or self.provider.model_version,
        )
