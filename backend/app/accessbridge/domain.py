"""Validated contracts shared by API, agents, persistence, and exports."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def identifier() -> str:
    return uuid4().hex


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


BlockType = Literal[
    "heading",
    "paragraph",
    "list",
    "activity",
    "question",
    "diagram",
    "safety",
    "glossary",
    "checkpoint",
    "materials",
]
Method = Literal["deterministic", "llm", "hybrid"]
CheckStatus = Literal["PASS", "FAIL", "WARN", "NEEDS_REVIEW"]
Severity = Literal["MUST", "SHOULD"]
OutputLanguage = Literal["en", "te", "hi"]


class SourceBlock(StrictModel):
    block_id: str = Field(min_length=1)
    block_type: BlockType
    text: str = Field(min_length=1)
    order_index: int = Field(ge=0)
    source_page: int | None = None
    source_heading: str | None = None


class LearningObjective(StrictModel):
    objective_id: str = Field(min_length=1)
    description: str = Field(min_length=8)
    source_block_ids: list[str] = Field(min_length=1)
    essential_concepts: list[str] = Field(min_length=1)
    required_vocabulary: list[str]


class SourceLesson(StrictModel):
    lesson_id: str = Field(default_factory=identifier)
    title: str
    subject: str = "Not yet analyzed"
    grade_level: str = "Not yet analyzed"
    source_filename: str
    source_format: Literal["pdf", "docx", "txt", "md"]
    blocks: list[SourceBlock] = Field(min_length=1)
    objectives: list[LearningObjective] = Field(default_factory=list)
    parsing_warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=timestamp)

    @model_validator(mode="after")
    def unique_blocks(self) -> Self:
        if len({b.block_id for b in self.blocks}) != len(self.blocks):
            raise ValueError("Duplicate source block IDs")
        return self


class AccommodationRequirement(StrictModel):
    accommodation_id: str
    title: str
    description: str
    severity: Severity
    verification_method: Method
    parameters: dict[str, int | float | str | bool]
    rationale: str


class LearnerProfile(StrictModel):
    profile_id: str
    teacher_visible_name: str
    description: str
    accommodation_requirements: list[AccommodationRequirement] = Field(min_length=1)
    is_synthetic: Literal[True] = True


class PlannedTransformation(StrictModel):
    accommodation_id: str
    source_block_ids: list[str] = Field(min_length=1)
    instruction: str


class AdaptationPlan(StrictModel):
    profile_id: str
    accommodation_ids: list[str]
    planned_transformations: list[PlannedTransformation] = Field(min_length=1)
    objective_preservation_strategy: str


class LessonAnalysis(StrictModel):
    summary: str
    title: str
    subject: str
    grade_level: str
    learning_objectives: list[LearningObjective] = Field(min_length=1, max_length=12)
    key_concepts: list[str]
    important_vocabulary: list[str]
    named_entities: list[str] | None = None
    identified_challenges: list[str]
    analysis_warnings: list[str]
    plans: list[AdaptationPlan] = Field(min_length=1, max_length=3)


class AdaptedBlock(StrictModel):
    block_id: str = Field(min_length=1)
    source_block_ids: list[str] = Field(min_length=1)
    block_type: BlockType
    content: str = Field(min_length=1, max_length=14000)
    objective_ids: list[str]
    accommodation_ids: list[str]
    order_index: int = Field(ge=0)
    teacher_review_suggested: bool
    change_summary: str = Field(default="", max_length=2000)
    change_rationale: str = Field(default="", max_length=3000)


class AdaptedDraft(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    blocks: list[AdaptedBlock] = Field(min_length=1, max_length=70)
    narration_script: str = Field(min_length=1, max_length=40000)

    @model_validator(mode="after")
    def unique_blocks(self) -> Self:
        if len({b.block_id for b in self.blocks}) != len(self.blocks):
            raise ValueError("Duplicate adapted block IDs")
        indices = [b.order_index for b in self.blocks]
        if indices != sorted(set(indices)):
            raise ValueError("Block order indices must be unique and ordered")
        return self


class ObjectiveTranslation(StrictModel):
    objective_id: str = Field(min_length=1)
    description: str = Field(min_length=8, max_length=2000)
    key_concepts: list[str] = Field(min_length=1, max_length=30)
    back_translation: str = Field(min_length=8, max_length=2000)
    uncertainty_notes: list[str] = Field(max_length=20)


class MultilingualDraft(AdaptedDraft):
    objective_translations: list[ObjectiveTranslation] = Field(
        min_length=1, max_length=12
    )


class VerificationCheck(StrictModel):
    check_id: str
    accommodation_id: str | None = None
    objective_id: str | None = None
    method: Method
    severity: Severity = "MUST"
    status: CheckStatus
    block_id: str | None = None
    evidence: str = ""
    explanation: str
    reason: str | None = None


class SemanticReview(StrictModel):
    checks: list[VerificationCheck]


class VerificationReport(StrictModel):
    verification_id: str = Field(default_factory=identifier)
    adaptation_id: str
    adaptation_version: int = Field(ge=1)
    checks: list[VerificationCheck]
    original_semantic_checks: list[VerificationCheck] = Field(default_factory=list)
    objectives_evaluated: list[str]
    accommodations_evaluated: list[str]
    mandatory_failures: list[str]
    warnings: list[str]
    requires_teacher_review: bool
    semantic_complete: bool
    verified_at: str = Field(default_factory=timestamp)


class TeacherApproval(StrictModel):
    version: int = Field(ge=1)
    approved_at: str = Field(default_factory=timestamp)
    review_note: str
    acknowledged_check_ids: list[str]
    qualified_language_review: bool = False


class TypographySettings(StrictModel):
    font_size: int = Field(default=11, ge=11, le=32)
    line_spacing: float = Field(default=1.7, ge=1.3, le=2.5)
    paragraph_spacing: int = Field(default=12, ge=4, le=32)
    letter_spacing: float = Field(default=0, ge=0, le=0.15)
    content_width: int = Field(default=48, ge=24, le=72)
    font_family: Literal["sans-serif", "serif"] = "sans-serif"
    high_contrast: bool = False


class AssessmentConfig(StrictModel):
    answer_keys: dict[str, Annotated[str, Field(min_length=1, max_length=2000)]] = (
        Field(min_length=1, max_length=50)
    )
    restricted_source_block_ids: list[str] = Field(default_factory=list, max_length=100)
    allow_word_bank: bool = False
    allow_alternative_response: bool = False


class AdaptedLesson(AdaptedDraft):
    adaptation_id: str = Field(default_factory=identifier)
    lesson_id: str
    profile_id: str
    version: int = Field(default=1, ge=1)
    created_at: str = Field(default_factory=timestamp)
    approval_status: Literal["DRAFT", "NEEDS_TEACHER_REVIEW", "APPROVED"] = "DRAFT"
    approval: TeacherApproval | None = None
    verification: VerificationReport | None = None
    output_language: OutputLanguage = "en"
    objective_translations: list[ObjectiveTranslation] = Field(default_factory=list)
    typography: TypographySettings = Field(default_factory=TypographySettings)
    block_decisions: dict[str, Literal["PENDING", "ACCEPTED", "REJECTED"]] = Field(
        default_factory=dict
    )
    assessment: AssessmentConfig | None = None


class CorrectionRequest(StrictModel):
    adaptation_id: str
    failed_check_ids: list[str]
    target_block_ids: list[str] = Field(min_length=1)
    failure_descriptions: list[str]
    required_changes: list[str]
    correction_round: int = Field(ge=1, le=2)


class CorrectionPatch(StrictModel):
    replacements: list[AdaptedBlock] = Field(min_length=1)


class AgentEvent(StrictModel):
    event_id: int = Field(ge=1)
    run_id: str
    agent_name: str
    event_type: str
    status: str
    timestamp: str = Field(default_factory=timestamp)
    message: str
    profile_id: str | None = None
    token_usage: dict[str, int] | None = None
    elapsed_ms: int | None = None


class CallRecord(StrictModel):
    agent_name: str
    provider: str
    model: str
    started_at: str
    ended_at: str | None = None
    elapsed_ms: int | None = None
    status: str
    attempt: int
    token_usage: dict[str, int] | None = None
    error_category: str | None = None
    provider_request_id: str | None = None
    input_sha256: str | None = None
    response_sha256: str | None = None


RunStatus = Literal[
    "QUEUED",
    "ANALYZING",
    "TRANSFORMING",
    "VERIFYING",
    "CORRECTING",
    "COMPLETED",
    "PARTIALLY_COMPLETED",
    "FAILED",
    "INTERRUPTED",
]


class RunRecord(StrictModel):
    run_id: str = Field(default_factory=identifier)
    lesson: SourceLesson
    profiles: list[LearnerProfile]
    status: RunStatus = "QUEUED"
    created_at: str = Field(default_factory=timestamp)
    completed_at: str | None = None
    model: str
    provider: str
    source: Literal["live", "recorded"] = "live"
    recorded_at: str | None = None
    max_correction_rounds: int = Field(default=1, ge=0, le=2)
    analysis: LessonAnalysis | None = None
    adaptations: dict[str, AdaptedLesson] = Field(default_factory=dict)
    profile_statuses: dict[str, str] = Field(default_factory=dict)
    profile_errors: dict[str, str] = Field(default_factory=dict)
    events: list[AgentEvent] = Field(default_factory=list)
    calls: list[CallRecord] = Field(default_factory=list)
    corrections: list[CorrectionRequest] = Field(default_factory=list)
    error: str | None = None
    output_language: OutputLanguage = "en"
    assessment: AssessmentConfig | None = None


class RunRequest(StrictModel):
    lesson_id: str
    profile_ids: list[str] = Field(min_length=1, max_length=3)
    max_correction_rounds: int = Field(default=1, ge=0, le=2)
    output_language: OutputLanguage = "en"
    assessment: AssessmentConfig | None = None


class BlockEdit(StrictModel):
    expected_version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=14000)


class BlockDecision(StrictModel):
    expected_version: int = Field(ge=1)
    status: Literal["ACCEPTED", "REJECTED"]


class BlockRegeneration(StrictModel):
    expected_version: int = Field(ge=1)
    instruction: str = Field(
        default="Improve the selected block using its documented accommodation requirements.",
        min_length=10,
        max_length=2000,
    )


class PresentationEdit(StrictModel):
    expected_version: int = Field(ge=1)
    typography: TypographySettings


class RationaleCard(StrictModel):
    block_id: str
    adaptation_version: int
    source_block_ids: list[str]
    accommodation_ids: list[str]
    change_summary: str
    rationale: str
    rationale_origin: Literal["model", "requirement_context"]
    checks: list[VerificationCheck]
    acceptance_status: Literal["PENDING", "ACCEPTED", "REJECTED"]


class AssessmentQuestionView(StrictModel):
    source_question_id: str
    original_question: str
    adapted_questions: list[str]
    correct_answer: str
    objective_ids: list[str]
    accommodation_rationale: list[str]
    verification: list[VerificationCheck]


class ReplayCall(StrictModel):
    agent_name: str
    provider: str
    model: str
    started_at: str
    ended_at: str | None
    elapsed_ms: int | None
    status: str
    retry_count: int
    token_usage: dict[str, int] | None
    error_category: str | None


class RunReplay(StrictModel):
    run_id: str
    historical: Literal[True] = True
    recorded_at: str
    status: str
    correction_rounds: int
    events: list[AgentEvent]
    calls: list[ReplayCall]


class ApprovalRequest(StrictModel):
    version: int = Field(ge=1)
    confirmation: Literal[True]
    review_note: str = Field(default="", max_length=3000)
    acknowledged_check_ids: list[str] = Field(default_factory=list)
    qualified_language_review: bool = False


class ExportRequest(StrictModel):
    run_id: str
    profile_ids: list[str] = Field(min_length=1)
    adaptation_versions: dict[str, int]


LIMITATIONS = [
    "Automated checks and AI judgments can miss problems. Teacher or specialist review is necessary.",
    "Diagram descriptions use source text and captions; source images are not interpreted. Review descriptions.",
    "Narration is a script; browser speech is a preview, not a recorded voice file.",
    "PDF tagging is limited; HTML is the primary accessible format. Screen-reader testing remains necessary.",
    "Demo profiles are synthetic and illustrative. Real support plans require qualified professionals.",
    "Lesson content is sent to the configured third-party AI provider. Do not upload confidential or identifying material.",
    "This tool supports teachers. It does not certify legal compliance.",
]


class ExportManifest(StrictModel):
    export_id: str = Field(default_factory=identifier)
    run_id: str
    lesson_id: str
    profile_ids: list[str]
    adaptation_versions: dict[str, int]
    approval_statuses: dict[str, str]
    included_files: list[str]
    verification_summary: dict[str, dict[str, int]]
    unresolved_issues: dict[str, list[VerificationCheck]]
    generated_at: str = Field(default_factory=timestamp)
    model: str
    draft_notice: str | None = None
    warnings: dict[str, list[str]] = Field(default_factory=dict)
    generation_config: dict[str, int | str | bool] = Field(default_factory=dict)
    approvals: dict[str, TeacherApproval | None] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=lambda: list(LIMITATIONS))


class Health(StrictModel):
    status: str = "ok"
    version: str = "2.0.0"
    database: str
    configured: bool
    provider: str
    model: str
    timestamp: str = Field(default_factory=timestamp)


class VersionSnapshot(StrictModel):
    adaptation: AdaptedLesson
    saved_at: str = Field(default_factory=timestamp)
    reason: str
