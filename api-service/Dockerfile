FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

# Run Uvicorn on start
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]