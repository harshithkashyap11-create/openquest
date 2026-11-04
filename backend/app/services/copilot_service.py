from uuid import UUID
from typing import Any
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.copilot import (
    ClassContextSummary,
    CopilotChatRequest,
    CopilotChatResponse,
)
from app.services.copilot_context import extract_classroom_context
from app.services.copilot_provider import (
    MockCopilotProvider,
    OpenRouterCopilotProvider,
    create_copilot_provider,
)
from app.subject_taxonomy import SUBJECT_TAXONOMY


class TeacherCopilotService:
    """Service orchestrating AI Teacher Copilot interactions.

    Guarantees:
    - Never modifies student records, diagnoses, grades, or interventions autonomously.
    - Uses allowlisted database functions for classroom context extraction.
    - Strictly scopes student data to the specified classroom ID.
    - Validates outputs against strict Pydantic schemas.
    """

    def __init__(
        self,
        db: Session,
        provider: MockCopilotProvider | OpenRouterCopilotProvider | None = None,
    ) -> None:
        self.db = db
        self.provider = provider or create_copilot_provider(get_settings())

    def chat(self, request: CopilotChatRequest) -> CopilotChatResponse:
        context_summary: ClassContextSummary | None = None
        grounding_text: str = ""

        if request.class_id is not None:
            context_summary, grounding_text = extract_classroom_context(
                self.db, request.class_id
            )

        response = self.provider.generate(
            request=request,
            context_summary=context_summary,
            grounding_text=grounding_text,
        )
        return response

    def get_classroom_context(self, class_id: UUID) -> ClassContextSummary:
        summary, _ = extract_classroom_context(self.db, class_id)
        return summary

    @staticmethod
    def get_supported_taxonomy() -> dict[str, list[dict[str, Any]]]:
        subjects: dict[str, list[dict[str, Any]]] = {}
        for (subject, topic), misconceptions in SUBJECT_TAXONOMY.items():
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(
                {
                    "topic": topic,
                    "misconceptions": [
                        {
                            "code": m.code,
                            "category": m.category,
                            "description": m.description,
                            "followup_question": m.followup_question,
                        }
                        for m in misconceptions
                    ],
                }
            )
        return subjects
