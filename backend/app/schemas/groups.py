from typing import Literal

from pydantic import BaseModel


class GroupReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    expected_revision: str | None = None


class GroupMemberResponse(BaseModel):
    student_id: str
    student_code: str


class LearningGroupResponse(BaseModel):
    id: str
    revision: str = ""
    class_id: str
    topic: str
    misconception_code: str
    name: str
    review_status: Literal["proposed", "approved", "rejected"]
    teacher_approved: bool
    members: list[GroupMemberResponse]


class GroupGenerationResponse(BaseModel):
    groups: list[LearningGroupResponse]
    followup_student_ids: list[str]
