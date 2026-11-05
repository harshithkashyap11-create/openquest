from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AttentionCounts(BaseModel):
    pending_diagnoses: int
    pending_reviews: int
    uncertain: int
    proposed_groups: int
    ready_for_reassessment: int


class ConceptSummary(BaseModel):
    code: str
    response_count: int
    student_count: int
    pending_reviews: int
    uncertain: int
    reviewed: int


class MapSummary(BaseModel):
    class_id: UUID
    subject: str
    topic: str
    queried_at: datetime
    period_from: datetime | None
    period_to: datetime | None
    total_responses: int
    total_students: int
    concepts: list[ConceptSummary]
    attention: AttentionCounts


class ReviewEvidence(BaseModel):
    code: str
    reason: str
    version: int
    teacher_id: UUID
    created_at: datetime


class ResponseEvidence(BaseModel):
    diagnosis_id: UUID
    submission_id: UUID
    student_id: UUID
    student_code: str
    question_id: UUID
    question_text: str
    answer: str | None
    student_explanation: str | None
    submitted_at: datetime
    suggested_at: datetime
    original_code: str
    effective_code: str
    confidence: float
    evidence_quote: str
    ai_explanation: str | None
    provider: str
    model_version: str | None
    uncertain: bool
    review: ReviewEvidence | None


class EvidencePage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ResponseEvidence]


class JourneyEvent(BaseModel):
    kind: Literal['response', 'support', 'practice', 'reassessment']
    source_id: UUID
    at: datetime
    assignment_id: UUID | None = None
    question_id: UUID | None = None
    question_text: str | None = None
    answer: str | None = None
    title: str | None = None
    status: str | None = None
    correct: int | None = None
    total: int | None = None


class JourneyPage(BaseModel):
    student_id: UUID
    subject: str
    topic: str
    total: int
    offset: int
    limit: int
    events: list[JourneyEvent]
