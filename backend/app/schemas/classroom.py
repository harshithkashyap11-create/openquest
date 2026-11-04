from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.interventions import ProgressAccuracy


class DemoClassResponse(BaseModel):
    id: UUID
    class_name: str
    subject: str
    topic: str
    student_count: int


class DemoStudentResolutionRequest(BaseModel):
    class_id: UUID
    student_code: str = Field(min_length=1, max_length=100)


class DemoStudentResolutionResponse(BaseModel):
    student_id: UUID
    class_id: UUID
    student_code: str


class DemoStudentResponse(BaseModel):
    student_id: UUID
    student_code: str


class AssessmentQuestionResponse(BaseModel):
    id: UUID
    question_text: str
    subject: str
    topic: str


class ClassAssessmentResponse(BaseModel):
    class_id: UUID
    title: str
    subject: str
    topic: str
    questions: list[AssessmentQuestionResponse]
    attempt_count: int = 0
    latest_attempt_no: int | None = None
    latest_attempt_answered: int = 0


class AssessmentAnswerRequest(BaseModel):
    question_id: UUID
    answer: str | None = Field(default=None, max_length=1000)
    explanation: str | None = Field(default=None, max_length=2000)


class AssessmentSubmissionRequest(BaseModel):
    request_id: str | None = Field(default=None, min_length=8, max_length=100)
    answers: list[AssessmentAnswerRequest] = Field(min_length=1, max_length=20)


class AssessmentSubmissionResponse(BaseModel):
    student_id: UUID
    attempt_no: int
    submitted_count: int


class StudentAssessmentStatus(BaseModel):
    student_id: UUID
    student_code: str
    attempt_no: int | None
    answered_questions: int
    diagnosed_answers: int
    pending_diagnoses: int


class AssessmentSummaryResponse(BaseModel):
    class_id: UUID
    total_students: int
    submitted_students: int
    total_questions_per_student: int
    answered_questions: int
    diagnosed_answers: int
    pending_diagnoses: int
    students: list[StudentAssessmentStatus]


class StudentProgressResponse(BaseModel):
    student_id: UUID
    student_code: str
    assigned_interventions: int
    completed_interventions: int
    completed_reassessments: int
    initial_assessment: ProgressAccuracy
    followup_assessment: ProgressAccuracy
    accuracy_change_percentage_points: float | None
    progress_interpretation: str
