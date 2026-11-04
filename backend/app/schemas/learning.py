from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class LessonExercise(StrictInput):
    prompt: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=1000)
    hints: list[str] = Field(min_length=1, max_length=4)

class WorkedExample(StrictInput):
    problem: str = Field(min_length=1, max_length=2000)
    steps: list[str] = Field(min_length=1, max_length=8)
    answer: str = Field(min_length=1, max_length=1000)

class LessonContent(StrictInput):
    title: str = Field(min_length=1, max_length=200)
    objectives: list[str] = Field(min_length=1, max_length=5)
    explanation: str = Field(min_length=1, max_length=6000)
    misconception_correction: str = Field(min_length=5, max_length=2000)
    worked_example: WorkedExample
    practice_questions: list[LessonExercise] = Field(min_length=1, max_length=5)
    exit_ticket: LessonExercise

    @model_validator(mode='after')
    def validate_readable_content(self):
        import json
        text = json.dumps(self.model_dump(), ensure_ascii=False)
        if '\\\\frac' in text or '$$' in text or '<script' in text.casefold():
            raise ValueError('Use readable plain text mathematics such as 1/2; unsupported markup is not accepted')
        groups = [self.objectives, self.worked_example.steps, *[q.hints for q in [*self.practice_questions, self.exit_ticket]]]
        if any(not s.strip() or len(s) > 2000 for group in groups for s in group):
            raise ValueError('Lesson sections must contain bounded nonempty text')
        return self

class GenerateLesson(StrictInput):
    misconception_code: str = Field(min_length=1, max_length=40)
    language: Literal['en', 'hi', 'te'] = 'en'
    request_id: str = Field(min_length=8, max_length=100)
    allow_fallback: bool = False
    difficulty: Literal['foundation', 'standard', 'challenging'] = 'standard'
    duration_minutes: int = Field(default=15, ge=5, le=60)

class AssignLesson(StrictInput):
    revision_id: UUID

class EditLesson(StrictInput):
    revision_id: UUID
    content: LessonContent

class ReviewLesson(StrictInput):
    revision_id: UUID
    action: Literal['approve', 'reject', 'publish', 'archive']
    answer_keys_reviewed: bool = False
    language_reviewed: bool = False
    reason: str = Field(default='', max_length=1000)

class HintRequest(StrictInput):
    request_id: str = Field(min_length=8, max_length=100)
    question_index: int = Field(ge=0, le=100)
    language: Literal['en', 'hi', 'te'] = 'en'
    response: str = Field(default='', max_length=1500)
    generation_mode: Literal['template', 'live'] = 'template'

class CorrectionInput(StrictInput):
    code: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=100)
