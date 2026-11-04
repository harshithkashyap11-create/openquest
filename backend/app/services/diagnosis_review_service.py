from sqlalchemy import select
from app.models.learning import DiagnosisCorrection


def latest_correction(db, diagnosis_id):
    return db.scalar(select(DiagnosisCorrection).where(DiagnosisCorrection.diagnosis_id == diagnosis_id)
        .order_by(DiagnosisCorrection.version.desc()).limit(1))
