"""Assessment presentation guards; no automatic change to the intended answer or difficulty."""

import re

from app.accessbridge.domain import VerificationCheck

KEY_MARKER = re.compile(
    r"\b(?:answer\s*key|correct\s*answers?|teacher[ -]only|solutions?\s*:)\b",
    re.IGNORECASE,
)


def normalize(value):
    return re.sub(r"\s+", " ", value).strip().casefold()


def leaked_answers(adapted):
    if adapted.assessment is None:
        return []
    content = normalize(
        "\n".join([adapted.title, *(b.content for b in adapted.blocks)])
    )
    return [
        qid
        for qid, answer in adapted.assessment.answer_keys.items()
        if re.search(r"(?<!\w)" + re.escape(normalize(answer)) + r"(?!\w)", content)
    ]


def prepare_assessment(lesson, config):
    known = {b.block_id for b in lesson.blocks}
    restricted = set(config.restricted_source_block_ids)
    if not restricted.issubset(known) or len(restricted) != len(
        config.restricted_source_block_ids
    ):
        raise ValueError(
            "Select unique source blocks from this lesson for teacher-only material."
        )
    safe_blocks = [b for b in lesson.blocks if b.block_id not in restricted]
    if not safe_blocks:
        raise ValueError("At least one student question must remain.")
    if any(KEY_MARKER.search(b.text) for b in safe_blocks):
        raise ValueError(
            "Mark answer-key and teacher-only source blocks as restricted before generating an assessment."
        )
    question_ids = {b.block_id for b in safe_blocks if b.block_type == "question"}
    if not question_ids or set(config.answer_keys) != question_ids:
        raise ValueError(
            "Provide exactly one teacher answer key for every detected student question."
        )
    return lesson.model_copy(update={"blocks": safe_blocks}, deep=True)


def assessment_checks(source, adapted):
    if adapted.assessment is None:
        return []
    ids = {b.block_id for b in source.blocks if b.block_type == "question"}
    mapping = {
        qid: [
            b
            for b in adapted.blocks
            if b.block_type == "question" and qid in b.source_block_ids
        ]
        for qid in ids
    }
    missing = [qid for qid, blocks in mapping.items() if len(blocks) != 1]
    leaks = leaked_answers(adapted)
    return [
        VerificationCheck(
            check_id="DET-ASSESS-COVERAGE",
            method="deterministic",
            status="FAIL" if missing else "PASS",
            explanation="Each source question must map to exactly one adapted question. Mappings do not establish equivalent difficulty.",
            evidence=", ".join(missing),
        ),
        VerificationCheck(
            check_id="DET-ASSESS-KEYS",
            method="deterministic",
            status="PASS" if set(adapted.assessment.answer_keys) == ids else "FAIL",
            explanation="Teacher answer-key IDs must match all source question IDs.",
        ),
        VerificationCheck(
            check_id="DET-ASSESS-LEAK",
            method="deterministic",
            status="FAIL" if leaks else "PASS",
            explanation="Exact teacher answers were detected in student material."
            if leaks
            else "No exact teacher answer string was detected. Paraphrases and hints still require semantic and teacher review.",
            evidence=", ".join(leaks),
        ),
        VerificationCheck(
            check_id="MANUAL-ASSESSMENT",
            method="hybrid",
            status="NEEDS_REVIEW",
            explanation="Review intended difficulty, expected answers, question wording and permitted supports. Teacher-supplied keys are not independently established ground truth.",
        ),
    ]


def assessment_questions(run, adapted):
    if adapted.assessment is None:
        return []
    checks = (
        adapted.verification.checks
        if adapted.verification
        and adapted.verification.adaptation_version == adapted.version
        else []
    )
    return [
        {
            "source_question_id": block.block_id,
            "original_question": block.text,
            "adapted_questions": [
                b.content
                for b in adapted.blocks
                if b.block_type == "question" and block.block_id in b.source_block_ids
            ],
            "correct_answer": adapted.assessment.answer_keys.get(block.block_id, ""),
            "objective_ids": sorted(
                {
                    oid
                    for b in adapted.blocks
                    if block.block_id in b.source_block_ids
                    for oid in b.objective_ids
                }
            ),
            "accommodation_rationale": [
                b.change_rationale
                for b in adapted.blocks
                if block.block_id in b.source_block_ids and b.change_rationale
            ],
            "verification": [
                c.model_dump(mode="json")
                for c in checks
                if c.check_id == f"SEM-ASSESS-{block.block_id}"
                or c.check_id.startswith("DET-ASSESS")
            ],
        }
        for block in run.lesson.blocks
        if block.block_type == "question"
    ]
