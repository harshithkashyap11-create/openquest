from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from time import perf_counter
from uuid import uuid4
from app.services.auth_service import authorize_request
from app.routes.auth import router as auth_router
from app.routes.learning import router as learning_router
from app.routes.tutoring import router as tutoring_router
from app.routes.misconception_map import router as map_router
from app.routes.studio import router as studio_router

from app.routes.quizzes import router as quizzes_router
from app.routes.diagnoses import router as diagnoses_router
from app.routes.classroom import router as classroom_router
from app.routes.copilot import router as copilot_router
from app.routes.groups import router as groups_router
from app.routes.health import router as health_router
from app.routes.interventions import router as interventions_router

app = FastAPI(
    title="ClassPulse AI API",
    description="Classroom intelligence backend foundation.",
    version="0.2.0",
    dependencies=[Depends(authorize_request)],
)
app.include_router(auth_router)
app.include_router(learning_router)
app.include_router(tutoring_router)
app.include_router(map_router)
app.include_router(studio_router)
app.include_router(health_router)
app.include_router(diagnoses_router)
app.include_router(groups_router)
app.include_router(interventions_router)
app.include_router(classroom_router)
app.include_router(copilot_router, prefix="/api/v1/copilot")
app.include_router(copilot_router, prefix="/api/copilot")

app.include_router(quizzes_router)


@app.exception_handler(IntegrityError)
@app.exception_handler(StaleDataError)
async def concurrent_update(request, _error):
    if getattr(request.state, "db", None) is not None:
        request.state.db.rollback()
    return JSONResponse(status_code=409, content={"detail": "CONCURRENT_UPDATE: refresh and retry the same request"})


@app.exception_handler(OperationalError)
async def database_unavailable(request, _error):
    if getattr(request.state, "db", None) is not None:
        request.state.db.rollback()
    return JSONResponse(status_code=503, content={"detail": "DATABASE_UNAVAILABLE: your request can be retried"})


@app.middleware("http")
async def request_metadata(request, call_next):
    start = perf_counter()
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Elapsed-Ms"] = str(round((perf_counter() - start) * 1000))
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
