# EvalKit - RAG Evaluation Platform

A comprehensive platform for evaluating Retrieval-Augmented Generation (RAG) systems with multi-stage evaluation, automated recommendations, and cost optimization.

## Features

- **Multi-Stage Evaluation Pipeline**: 3-stage pipeline (deterministic → small model → large model) for 87-90% cost savings
- **RAGAS + DeepEval Metrics**: Faithfulness, answer relevancy, context precision/recall, hallucination detection
- **AutoFix Engine**: Rule-based recommendations for improving RAG performance
- **Gate Policy Engine**: Configurable thresholds with severity classification (P0-P3)
- **Two-Tier Caching**: Redis (hot) + Postgres (cold) for fast evaluations
- **Python SDK**: Simple API client, `@observe` decorator, context manager

## Quick Start

```bash
# Start services
docker-compose up -d

# Run database migrations
docker exec -it evalkit-api-1 alembic upgrade head

# Seed test data
docker cp backend/seed.py evalkit-api-1:/app/seed.py
docker exec -it evalkit-api-1 python seed.py
```

## API Usage

```bash
curl -X POST http://localhost:8000/v1/evaluate \
  -H "Authorization: Bearer pk_test_evalkit123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<PROJECT_ID>",
    "query": "What is RAG?",
    "response": "RAG is Retrieval Augmented Generation...",
    "context": ["RAG stands for..."]
  }'
```

## SDK Usage

```python
from evalkit import EvalClient

client = EvalClient(api_key="pk_test_xxx")
result = client.evaluate(
    project_id="...",
    query="What is RAG?",
    response="RAG is...",
    context=["RAG stands for..."]
)

print(result.metrics.faithfulness)  # 0.92
print(result.decision)  # "pass"
```

## Architecture

```
evalkit/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API endpoints
│   │   ├── core/            # Pipeline, gate policy, autofix
│   │   ├── cache/           # Two-tier caching
│   │   └── security/        # API key auth
│   └── alembic/             # Database migrations
├── sdk/                     # Python SDK
└── docker-compose.yml
```

## Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:3000
```

## License

MIT
