import asyncio

import httpx
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


async def _get_health_responses():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get("/health"), await client.get("/health/ready")


async def _get_readiness_response():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get("/health/ready")


def test_health_and_database_readiness(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        health_response, readiness_response = asyncio.run(_get_health_responses())
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert readiness_response.status_code == 200
    assert readiness_response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_503_when_database_fails():
    class UnavailableSession:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    def override_get_db():
        yield UnavailableSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = asyncio.run(_get_readiness_response())
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
