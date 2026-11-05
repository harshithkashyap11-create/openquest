import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.warning("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
    return {"status": "ready", "database": "ok"}


@router.get('/health/ai')
def ai_configuration():
    from app.core.config import get_settings
    settings = get_settings()
    provider = settings.ai_provider
    configured = bool(settings.gemini_api_key if provider == 'gemini' else settings.openrouter_api_key if provider == 'openrouter' else True)
    return {'provider': provider, 'model': settings.gemini_model if provider == 'gemini' else settings.openrouter_model if provider == 'openrouter' else 'rules-v1',
        'credentials_configured': configured, 'live_readiness': 'NOT_TESTED',
        'note': 'Configuration check only. Run scripts.probe_ai --live for an actual bounded provider check.'}


@router.get('/api/system-status')
def system_status(db: Session = Depends(get_db)):
    """Authenticated local status; no provider requests or infrastructure values."""
    from app.core.config import get_settings
    settings = get_settings()
    database = 'available'
    try:
        db.execute(text('SELECT 1'))
    except SQLAlchemyError:
        db.rollback()
        database = 'unavailable'
    configured = settings.ai_provider == 'mock' or bool(
        settings.gemini_api_key if settings.ai_provider == 'gemini'
        else settings.openrouter_api_key and settings.openrouter_model)
    return dict(app='available', database=database, ai_provider='configured' if configured else 'unavailable',
        provider_reachability='not_tested', checked_at=datetime.now(timezone.utc).isoformat())
