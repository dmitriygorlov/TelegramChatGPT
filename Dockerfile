FROM python:3.15.2-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN useradd --uid 10001 --create-home appuser
USER appuser
CMD ["python","tg_bot_eng.py"]

FROM base AS test
USER root
RUN pip install -r requirements-dev.txt
USER appuser
CMD ["sh", "-c", "python -m pytest -q -p no:cacheprovider && python -m pip check && ruff check --no-cache ."]

FROM base AS runtime
