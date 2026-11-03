from fastapi import Depends, FastAPI
from app.services.auth_service import authorize_request
from app.routes.auth import router as auth_router

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
app.include_router(health_router)
app.include_router(diagnoses_router)
app.include_router(groups_router)
app.include_router(interventions_router)
app.include_router(classroom_router)
app.include_router(copilot_router, prefix="/api/v1/copilot")
app.include_router(copilot_router, prefix="/api/copilot")

app.include_router(quizzes_router)
