FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

COPY src /app/src
COPY db /app/db

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
