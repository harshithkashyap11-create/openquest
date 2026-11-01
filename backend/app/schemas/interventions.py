from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InterventionPersonalization(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    explanation: str = Field(min_length=1, max_length=1200)
    instructions: str = Field(min_length=1, max_length=800)
    introduction: str = Field(min_length=1, max_length=300)
    hints: list[Annotated[str, Field(min_length=1, max_length=180)]] = Field(
        min_length=1, max_length=3
    )


class PracticeQuestionResponse(BaseModel):
    question_index: int
    question: str
    hint: str


class InterventionContentResponse(BaseModel):
    id: UUID
    group_id: UUID
    subject: str
    topic: str
    misconception_code: str
    title: str
    learning_objective: str
    explanation: str
    introduction: str
    guided_example: dict[str, str]
    practice_questions: list[str]
    expected_answers: list[str]
    instructions: str
    hints: list[str]
    provider: str
    generation_note: str | None


class StudentInterventionResponse(BaseModel):
    id: UUID
    subject: str
    topic: str
    misconception_code: str
    title: str
    learning_objective: str
    explanation: str
    introduction: str
    guided_example: dict[str, str]
    practice_questions: list[PracticeQuestionResponse]
    instructions: str


class PracticeResponseItem(BaseModel):
    question_index: int
    answer: str | None
    is_correct: bool
    submitted_at: str


class InterventionAssignmentResponse(BaseModel):
    id: UUID
    intervention_id: UUID
    student_id: UUID
    status: Literal["assigned", "in_progress", "completed"]
    assigned_at: str
    started_at: str | None
    completed_at: str | None
    intervention: StudentInterventionResponse
    practice_responses: list[PracticeResponseItem] = Field(default_factory=list)


class InterventionGenerationResponse(BaseModel):
    intervention: InterventionContentResponse
    assignments_created: int
    assignments: list[InterventionAssignmentResponse]


class PracticeAnswer(BaseModel):
    question_index: int = Field(ge=0)
    answer: str | None = Field(default=None, max_length=200)


class PracticeSubmissionRequest(BaseModel):
    answers: list[PracticeAnswer] = Field(min_length=1)


class PracticeResultResponse(BaseModel):
    question_index: int
    is_correct: bool


class PracticeSubmissionResponse(BaseModel):
    assignment_id: UUID
    status: Literal["assigned", "in_progress", "completed"]
    correct_answers: int
    incorrect_answers: int
    results: list[PracticeResultResponse]


class ReassessmentQuestionResponse(BaseModel):
    id: UUID
    question: str


class ReassessmentResultResponse(BaseModel):
    question_id: UUID
    answer: str | None
    is_correct: bool


class ReassessmentResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    misconception_code: str
    status: Literal["pending", "completed"]
    questions: list[ReassessmentQuestionResponse]
    total_questions: int
    correct_answers: int | None
    incorrect_answers: int | None
    accuracy_percentage: float | None
    results: list[ReassessmentResultResponse] = Field(default_factory=list)


class InterventionCompletionResponse(BaseModel):
    assignment: InterventionAssignmentResponse
    reassessment: ReassessmentResponse


class ReassessmentAnswer(BaseModel):
    question_id: UUID
    answer: str | None = Field(default=None, max_length=200)


class ReassessmentSubmissionRequest(BaseModel):
    answers: list[ReassessmentAnswer] = Field(default_factory=list)


class ReassessmentSubmissionResponse(ReassessmentResponse):
    pass


class ProgressAccuracy(BaseModel):
    accuracy_percentage: float | None
    sample_size: int
    correct_answers: int


class StudentSupportResponse(BaseModel):
    student_id: UUID
    student_code: str
    misconception_code: str
    reason: str
    followup_accuracy_percentage: float | None
    sample_size: int


class ClassProgressResponse(BaseModel):
    class_id: UUID
    assigned_interventions: int
    completed_interventions: int
    completed_reassessments: int
    initial_assessment: ProgressAccuracy
    followup_assessment: ProgressAccuracy
    accuracy_change_percentage_points: float | None
    progress_interpretation: str
    students_needing_support: list[StudentSupportResponse]
