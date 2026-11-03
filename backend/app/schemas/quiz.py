from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Option = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class RepairInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: ShortText
    options: list[Option] = Field(min_length=2, max_length=4)
    correct_option: int = Field(ge=0, le=3, strict=True)
    explanation: ShortText
    hint: ShortText

    @model_validator(mode="after")
    def valid_options(self):
        if self.correct_option >= len(self.options):
            raise ValueError("Correct option must be one of the available options")
        if len({value.casefold() for value in self.options}) != len(self.options):
            raise ValueError("Options must be distinct")
        return self


class QuestionInput(RepairInput):
    # A teacher-approved follow-up is optional; the model never invents its key.
    hint: str = Field(default="", max_length=2000)
    concept: str = Field(default="", max_length=200)
    repair: RepairInput | None = None


class QuizInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)
    ]
    questions: list[QuestionInput] = Field(min_length=1, max_length=20)


class ImportInput(BaseModel):
    content: str = Field(min_length=1, max_length=200_000)


class QuizAnswer(BaseModel):
    question_id: UUID
    selected_option: int = Field(ge=0, le=3, strict=True)


class SubmitQuizInput(BaseModel):
    answers: list[QuizAnswer] = Field(min_length=1, max_length=20)


class ReflectionInput(BaseModel):
    message: ShortText
    language: Literal["en", "hi", "te"] = "en"


class RepairAnswerInput(BaseModel):
    selected_option: int = Field(ge=0, le=3, strict=True)


class ReviewInput(BaseModel):
    flagged: bool


class LessonReviewInput(BaseModel):
    status: Literal["draft", "accepted", "rejected"]
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)
    ]


class TutorOutput(BaseModel):
    error_type: Literal["concept", "procedure", "misread", "uncertain"]
    evidence: str = Field(max_length=2000)
    reply: ShortText
