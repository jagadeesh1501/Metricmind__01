FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY data/ data/
COPY outputs/ outputs/

WORKDIR /app/backend

# Make sure the semantic layer has clean data to load if the volume mount
# is empty on first run.
RUN python3 data_pipeline/cleaning.py || true

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
