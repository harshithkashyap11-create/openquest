from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Teacher query or instruction")
    class_id: UUID | None = Field(default=None, description="Optional active classroom ID")
    subject: str | None = Field(default=None, description="Optional subject override (e.g. Mathematics, Science, English)")
    topic: str | None = Field(default=None, description="Optional topic override (e.g. Fractions, Force and motion)")
    history: list[ChatMessage] = Field(default_factory=list, description="Prior conversation messages")
    action: str | None = Field(
        default=None,
        description="Optional capability action preset (e.g. summarize_class, struggling_students, generate_worksheet, lesson_plan, remedial_exercise)",
    )


class MisconceptionStat(BaseModel):
    code: str
    category: str
    description: str
    student_count: int
    affected_students: list[str] = Field(default_factory=list)
    sample_evidence: list[str] = Field(default_factory=list)


class ClassContextSummary(BaseModel):
    class_id: UUID
    class_name: str
    subject: str
    topic: str
    total_students: int
    submitted_students: int
    answered_questions: int
    diagnosed_answers: int
    pending_diagnoses: int
    baseline_accuracy: float | None = None
    baseline_sample_size: int = 0
    reassessment_accuracy: float | None = None
    reassessment_sample_size: int = 0
    accuracy_delta: float | None = None
    top_misconceptions: list[MisconceptionStat] = Field(default_factory=list)
    students_needing_attention: list[str] = Field(default_factory=list)
    groups_count: int = 0
    approved_groups_count: int = 0
    assigned_interventions_count: int = 0


class DraftContentItem(BaseModel):
    question: str
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    hints: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"] | str | None = "intermediate"
    targeted_misconception: str | None = None


class LessonPhase(BaseModel):
    phase_name: str
    duration_minutes: int
    teacher_action: str
    student_action: str


class DraftLessonPlan(BaseModel):
    title: str
    subject: str
    topic: str
    duration_minutes: int = 45
    objectives: list[str] = Field(default_factory=list)
    materials_needed: list[str] = Field(default_factory=list)
    phases: list[LessonPhase] = Field(default_factory=list)
    differentiation: dict[str, str] = Field(default_factory=dict)
    assessment_check: str = ""


class DraftActivity(BaseModel):
    activity_name: str
    instructions: str
    group_size: str = "Small groups of 3-4"
    materials_needed: list[str] = Field(default_factory=list)
    expected_takeaway: str = ""


class DraftEducationalContent(BaseModel):
    content_type: Literal[
        "worksheet",
        "quiz",
        "lesson_plan",
        "practice_questions",
        "remedial_exercise",
        "classroom_activity",
    ] | str
    title: str
    target_audience: str = "all"
    misconception_code: str | None = None
    items: list[DraftContentItem] = Field(default_factory=list)
    lesson_plan: DraftLessonPlan | None = None
    activity: DraftActivity | None = None
    is_draft: bool = True


class CopilotChatResponse(BaseModel):
    reply: str
    intent: Literal[
        "classroom_intelligence",
        "teaching_assistance",
        "content_generation",
        "conversational",
    ] | str
    subject: str
    topic: str
    class_id: UUID | None = None
    class_context_summary: ClassContextSummary | None = None
    draft_content: DraftEducationalContent | None = None
    suggested_followups: list[str] = Field(default_factory=list)
    provider: str
    model_version: str
