FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN uv pip install --system -e ".[dev]"

ENV PYTHONPATH=/app/src

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "opentime.main:app", "--host", "0.0.0.0", "--port", "8000"]
