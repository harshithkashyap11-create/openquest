from fastapi import FastAPI

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
)
app.include_router(health_router)
app.include_router(diagnoses_router)
app.include_router(groups_router)
app.include_router(interventions_router)
app.include_router(classroom_router)
app.include_router(copilot_router, prefix="/api/v1/copilot")
app.include_router(copilot_router, prefix="/api/copilot")
