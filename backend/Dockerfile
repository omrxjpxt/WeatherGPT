# syntax=docker/dockerfile:1

# Stage 1: Build virtual environment with production dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --upgrade pip && \
    pip install .

# Stage 2: Minimal non-root production runtime
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    ENVIRONMENT=production

# Copy isolated virtualenv
COPY --from=builder /opt/venv /opt/venv

# Create unprivileged runtime user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser && \
    chown -R appuser:appgroup /app

# Copy application code with unprivileged ownership
COPY --chown=appuser:appgroup app /app/app

USER appuser

EXPOSE 8000

# Native healthcheck using standard library urllib (no external curl binary needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').getcode() == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
