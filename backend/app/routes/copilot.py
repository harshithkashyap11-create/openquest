from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.copilot import (
    ClassContextSummary,
    CopilotChatRequest,
    CopilotChatResponse,
)
from app.services.copilot_service import TeacherCopilotService
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
)

router = APIRouter(tags=["copilot"])


@router.post(
    "/chat",
    response_model=CopilotChatResponse,
    summary="Chat with AI Teacher Copilot",
    description="Context-aware AI teaching assistant supporting classroom intelligence, teaching strategies, lesson plans, and draft content generation.",
)
def chat_with_copilot(
    request: CopilotChatRequest,
    db: Session = Depends(get_db),
) -> CopilotChatResponse:
    try:
        service = TeacherCopilotService(db)
        return service.chat(request)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ProviderRateLimited as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
            headers={"Retry-After": "30"},
        ) from error
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/classes/{class_id}/context",
    response_model=ClassContextSummary,
    summary="Get verified classroom intelligence context",
    description="Retrieves ground-truth metrics, submission statistics, and diagnosed misconceptions for a classroom.",
)
def get_classroom_intelligence_context(
    class_id: UUID,
    db: Session = Depends(get_db),
) -> ClassContextSummary:
    try:
        service = TeacherCopilotService(db)
        return service.get_classroom_context(class_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/taxonomy",
    summary="List supported subjects and topics",
    description="Returns available subjects, topics, and misconception codes supported by the AI Teacher Copilot.",
)
def list_supported_taxonomy() -> dict:
    return TeacherCopilotService.get_supported_taxonomy()
