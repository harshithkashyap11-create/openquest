from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AssignmentReassessmentQuestion(BaseModel):
    question_id: UUID
    question_text: str
    answer: str | None
    is_correct: bool | None


class TeacherAssignmentReport(BaseModel):
    assignment_id: UUID
    student_id: UUID
    student_code: str
    intervention_id: UUID
    title: str
    misconception_code: str
    status: str
    assigned_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    reassessment_status: str | None
    reassessment_correct_answers: int | None
    reassessment_incorrect_answers: int | None
    reassessment_total_questions: int | None
    reassessment_accuracy_percentage: float | None
    reassessment_results: list[AssignmentReassessmentQuestion]
