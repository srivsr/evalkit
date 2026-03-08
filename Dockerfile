FROM python:3.11-slim

WORKDIR /app

# 1) Install curl (for lightweight HEALTHCHECK)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY evalkit/ evalkit/

RUN pip install --no-cache-dir .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/v1/health'); r.raise_for_status()"

CMD ["uvicorn", "evalkit.main:app", "--host", "0.0.0.0", "--port", "8000"]
