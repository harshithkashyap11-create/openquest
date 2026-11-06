from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudioQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    kind: Literal['choice', 'multiple_select', 'true_false', 'numeric', 'short_answer', 'writing', 'matching', 'categorize'] = 'choice'
    text: str = Field(min_length=1, max_length=4000)
    options: list[str] = Field(default_factory=list, max_length=12)
    items: list[str] = Field(default_factory=list, max_length=20)
    answer: Any = None
    explanation: str = Field(default='', max_length=4000)
    hint: str = Field(default='', max_length=2000)
    standard: str = Field(default='', max_length=160)
    concept: str = Field(default='', max_length=200)
    points: int = Field(default=1, ge=1, le=20)
    tolerance: float = Field(default=0, ge=0, le=100)
    distractors: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_key(self):
        for text in [*self.options, *self.items, *self.distractors.values()]:
            if not isinstance(text, str) or not text.strip() or len(text) > 1000:
                raise ValueError('Options, items and distractor explanations must be nonempty short text')
        if len(set(self.options)) != len(self.options) or len(set(self.items)) != len(self.items):
            raise ValueError('Options and items must be distinct')
        if self.kind in {'choice', 'true_false', 'multiple_select'}:
            if len(self.options) < 2 or (self.kind == 'true_false' and len(self.options) != 2):
                raise ValueError('Provide at least two choices (exactly two for true/false)')
            keys = self.answer if self.kind == 'multiple_select' else [self.answer]
            if not isinstance(keys, list) or not keys or len(set(map(str, keys))) != len(keys) or any(type(i) is not int or i < 0 or i >= len(self.options) for i in keys):
                raise ValueError('Choose valid answer option indexes')
        elif self.kind in {'matching', 'categorize'}:
            if not self.items or not self.options or not isinstance(self.answer, dict) or set(self.answer) != set(self.items) or any(v not in self.options for v in self.answer.values()):
                raise ValueError('Map every item to an available option')
        elif self.kind in {'numeric', 'short_answer'}:
            if not isinstance(self.answer, str) or not self.answer.strip() or len(self.answer) > 2000:
                raise ValueError('Provide a text answer key')
            if self.kind == 'numeric':
                from fractions import Fraction
                try:
                    Fraction(self.answer.strip())
                except (ValueError, ZeroDivisionError, OverflowError) as error:
                    raise ValueError('Numeric keys must be numbers or fractions') from error
        if self.kind == 'writing':
            self.answer = None
        return self


class ActivityInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    questions: list[StudioQuestion] = Field(min_length=1, max_length=40)
    max_attempts: int = Field(default=3, ge=1, le=10)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError('Question IDs must be unique')
        return self


class WorkInput(BaseModel):
    request_id: UUID
    answers: dict[str, Any]
    reasoning: dict[str, str] = Field(default_factory=dict)
    media: dict[str, dict] = Field(default_factory=dict)

    @model_validator(mode='after')
    def limit_payload(self):
        import json
        if len(json.dumps(self.answers)) > 100_000 or len(json.dumps(self.reasoning)) > 100_000 or len(json.dumps(self.media)) > 4_000_000:
            raise ValueError('Submission exceeds the supported size')
        return self


class SetInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    activity_ids: list[UUID] = Field(min_length=1, max_length=20)
    minimum_percent: int = Field(default=0, ge=0, le=100)


class GradeInput(BaseModel):
    question_id: str
    points: int = Field(ge=0, le=20)
    comment: str = Field(default='', max_length=4000)


class QRInput(BaseModel):
    activity_id: UUID
    question_id: str


class QRResponseInput(BaseModel):
    student_id: UUID
    option: int = Field(ge=0, le=3)


class PDFInput(BaseModel):
    filename: str = Field(max_length=200)
    content_base64: str = Field(min_length=1, max_length=10_000_000)


class GenerateInput(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    count: int = Field(default=3, ge=1, le=10)
    difficulty: Literal['easier', 'standard', 'harder'] = 'standard'
    kind: Literal['choice', 'numeric', 'short_answer', 'writing'] = 'choice'


class FeedbackInput(BaseModel):
    question_id: str
    message: str = Field(min_length=1, max_length=2000)
    language: Literal['en', 'hi', 'te'] = 'en'
