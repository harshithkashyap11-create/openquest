from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="ClassPulse AI Service",
    description="CrewAI and LLM-powered diagnostic and intervention service for ClassPulse",
    version="1.0.0"
)

AI_SERVICE_SECRET = os.getenv("AI_SERVICE_SECRET", "dev_ai_secret_classpulse_2026")

class DiagnosticRequest(BaseModel):
    student_id: str
    assessment_id: str
    question_text: str
    selected_option: str
    is_correct: bool
    detected_misconception: dict | None = None

def verify_token(x_api_secret: str = Header(None)):
    if x_api_secret and x_api_secret != AI_SERVICE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API Secret")
    return True

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ai-service",
        "crewai_ready": True
    }

@app.post("/diagnose")
def diagnose_student_gap(request: DiagnosticRequest, authorized: bool = Depends(verify_token)):
    """
    Day 2 diagnostic hook: CrewAI agent analysis of student misconceptions and personalized learning recommendations.
    """
    return {
        "student_id": request.student_id,
        "status": "received",
        "agent_analysis": "Diagnostic service ready for Day 2 agent pipeline integration."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
