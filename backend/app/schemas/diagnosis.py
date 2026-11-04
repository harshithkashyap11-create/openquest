from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.subject_taxonomy import all_misconception_codes, is_follow_up_code

MisconceptionCode = str
ProviderName = Literal["mock", "openrouter", "gemini"]


class DiagnosisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    misconception_code: MisconceptionCode = Field(
        validation_alias=AliasChoices("misconception_code", "primary_code")
    )
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(default="", max_length=1000)
    misconception_description: str = Field(default="", max_length=500)
    misunderstanding_explanation: str = Field(default="", max_length=1200)
    suggested_intervention: str = Field(default="", max_length=800)
    needs_followup: bool = False
    followup_question: str | None = Field(default=None, max_length=500)
    provider: ProviderName = "mock"
    status: Literal[
        "provisional", "needs_followup", "teacher_reviewed", "confirmed", "rejected"
    ] = "provisional"
    model_version: str | None = None

    @field_validator("misconception_code")
    @classmethod
    def validate_misconception_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in all_misconception_codes():
            raise ValueError("misconception_code is not in the supported taxonomy")
        return normalized

    @property
    def primary_code(self) -> str:
        return self.misconception_code


def validate_evidence_quotes(
    result: DiagnosisResult, answer: str | None, explanation: str | None
) -> None:
    quote = result.evidence
    if (
        not is_follow_up_code(result.misconception_code)
        and result.misconception_code != "CORRECT"
        and not quote.strip()
    ):
        raise ValueError("evidence quote must not be empty for a diagnosed misconception")
    if quote and quote not in (answer or "") and quote not in (explanation or ""):
        raise ValueError("evidence quote must appear verbatim in the answer or explanation")


class DiagnosisItem(BaseModel):
    id: str | None = None
    correction_version: int = 0
    effective_code: str | None = None
    submission_id: str
    student_id: str
    student_code: str
    misconception_code: MisconceptionCode
    subject: str
    topic: str
    confidence: float = Field(ge=0, le=1)
    evidence: str
    misconception_description: str = ""
    misunderstanding_explanation: str = ""
    suggested_intervention: str = ""
    needs_followup: bool
    followup_question: str | None
    provider: ProviderName
    status: str
    model_version: str | None


class DiagnosisBatchResponse(BaseModel):
    diagnosed: int
    failed: int
    timed_out: int
    rate_limited: int
    remaining_pending: int
    diagnoses: list[DiagnosisItem]
    errors: list[str]


class DiagnosisSummary(BaseModel):
    total_diagnoses: int
    by_code: dict[str, int]
    correct_count: int
    followup_count: int
