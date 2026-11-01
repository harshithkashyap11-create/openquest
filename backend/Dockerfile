FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/openpost

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/alembic.ini backend/alembic.ini
COPY backend/alembic backend/alembic
COPY backend/app backend/app
COPY backend/scripts backend/scripts
COPY backend/tests backend/tests
COPY backend/pytest.ini backend/pytest.ini
COPY data/synthetic_responses.csv data/synthetic_responses.csv
COPY docs docs

WORKDIR /workspace/openpost/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
