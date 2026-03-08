# EvalKit

QA-Grade RAG Evaluation Platform with a 6-layer cascading pipeline that diagnoses **why** your RAG system fails, not just **that** it fails.

## Architecture

EvalKit runs every query through a deterministic evaluation cascade:

```
Query + Context + Response
        |
   Layer A  ── Retrieval metrics (Precision@K, Recall@K, MRR, NDCG)
        |
   Layer C  ── Claim decomposition & verification
        |
   Layer B  ── Generation quality (faithfulness, relevance, completeness)
        |
  Layer D.0 ── Answerability classification
        |
   Layer D  ── Root cause attribution (17 diagnostic codes)
        |
   Anomaly  ── Regression detection, fix suggestions, cost tracking
```

### 17 Root Cause Codes

| Severity | Codes |
|----------|-------|
| **Blocker** | `INPUT_INVALID`, `NO_CONTEXT_PROVIDED`, `NO_RESPONSE_GENERATED` |
| **Critical** | `SHOULD_HAVE_REFUSED`, `HALLUCINATION`, `RETRIEVAL_MISS`, `NO_RELEVANT_DOCS_RETRIEVED` |
| **Major** | `GENERATION_UNFAITHFUL`, `EVIDENCE_NOT_USED`, `OFF_TOPIC_RESPONSE`, `EXCESSIVE_NOISE`, `FALSE_REFUSAL`, `CHUNK_BOUNDARY_BROKEN`, `EMBEDDING_DOMAIN_MISMATCH`, `EMBEDDING_DRIFT` |
| **Minor** | `CHUNK_INCOHERENT`, `CHUNK_TOO_SPARSE`, `CHUNK_TOO_DENSE` |

### Judge Abstraction

Pluggable AI judges with consensus support:
- **OpenAI** — GPT-4o, GPT-4-turbo
- **Anthropic** — Claude Sonnet, Claude Haiku
- **Consensus** — Multi-judge agreement with escalation

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.11 |
| Database | aiosqlite (async SQLite) |
| Auth | Clerk (JWT) |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| UI Components | shadcn/ui (Radix) + Recharts |
| Payments | PayPal, Razorpay, Payoneer |
| Deployment | Docker Compose |

## Project Structure

```
evalkit/                    # Python backend
  main.py                   # FastAPI app (API endpoints)
  config.py                 # Pydantic settings
  auth.py                   # Clerk authentication
  judges/                   # AI judge implementations
    base.py                 #   Abstract base
    openai_judge.py         #   GPT-4o / GPT-4-turbo
    anthropic_judge.py      #   Claude models
    consensus.py            #   Multi-judge consensus
    escalation.py           #   Disagreement escalation
    hallucination_tier.py   #   Hallucination severity tiers
  layers/                   # Evaluation pipeline
    retrieval.py            #   Layer A: Precision, Recall, MRR, NDCG
    claims.py               #   Layer C: Claim decomposition & verification
    generation.py           #   Layer B: Faithfulness, relevance, completeness
    answerability.py        #   Layer D.0: Answerable / partial / unanswerable
    root_cause.py           #   Layer D: 17 root cause codes
    anomaly.py              #   Anomaly detection
    fix_suggestions.py      #   Actionable fix recommendations
    cost_tracker.py         #   LLM cost estimation
    chunk_quality.py        #   Chunk boundary & coherence
    embedding_fitness.py    #   Embedding domain fitness
  models/                   # Pydantic schemas
    enums.py                #   Verdict, Severity, RootCauseCode
    request.py              #   API request models
    response.py             #   API response models
  regression/               # Regression detection
    detector.py             #   Quality regression analyzer
  reporting/                # Report generation
    json_report.py          #   JSON export
    markdown_report.py      #   Markdown export
  storage/                  # Persistence
    sqlite.py               #   Async SQLite storage
  api_keys.py               # API key management
  payment.py                # Payment processing
  subscriptions.py          # Quota enforcement
  rate_limit.py             # Rate limiting
  legal.py                  # Terms, privacy, refund
  cli.py                    # CLI commands

evalkit-ui/                 # Next.js 14 frontend
  app/                      # App Router pages
    dashboard/              #   Evaluation dashboard
    pricing/                #   Pricing page
    sign-in/, sign-up/      #   Clerk auth
    privacy/, terms/, refund/ # Legal pages
  components/
    eval/                   #   CascadeViz, ClaimsTable, RootCauseCard, etc.
    dashboard/              #   EvaluationTable, HealthIndicator, Sidebar
    landing/                #   Hero, FeatureGrid, HowItWorks
    ui/                     #   shadcn/ui components

docs/                       # Documentation
  evalkit_techniques.xlsx   #   38 evaluation techniques with formulas & thresholds
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/evaluate` | Run full 6-layer evaluation |
| `POST` | `/v1/evaluate/chunks` | Evaluate chunk quality |
| `POST` | `/v1/evaluate/embedding-fitness` | Evaluate embedding fitness |
| `POST` | `/v1/compare` | Compare two evaluation runs |
| `GET` | `/v1/runs/{run_id}` | Get evaluation results |
| `GET` | `/v1/runs` | List evaluation runs |
| `GET` | `/v1/health` | Health check |
| `POST` | `/v1/projects` | Create project |
| `GET` | `/v1/projects` | List projects |

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/srivsr/evalkit.git
cd evalkit
cp .env.example .env
# Fill in at least one judge API key (OpenAI or Anthropic)
```

### 2. Run with Docker

```bash
docker compose up --build
```

- Backend: http://localhost:8001
- Frontend: http://localhost:3004

### 3. Run locally (dev)

**Backend:**
```bash
pip install -e .
uvicorn evalkit.main:app --port 8000 --reload
```

**Frontend:**
```bash
cd evalkit-ui
npm install
npm run dev
```

### 4. CLI

```bash
pip install -e .
evalkit --help
```

## Evaluation Techniques

The `docs/evalkit_techniques.xlsx` spreadsheet documents all 38 evaluation techniques across the pipeline:

- **Layer A (Retrieval):** Precision@K, Recall@K, MRR, NDCG, Context Relevance
- **Layer C (Claims):** Claim decomposition, claim verification, context coverage
- **Layer B (Generation):** Faithfulness, relevance, completeness, coherence
- **Layer D.0 (Answerability):** Answerable / partially / unanswerable classification
- **Layer D (Root Cause):** 17 diagnostic root cause codes with severity mapping
- **Anomaly Detection:** Regression flags, threshold alerts
- **Fix Suggestions:** Actionable remediation per root cause

Each technique includes: formula/logic, examples, thresholds, RAG relationship, data flow (inputs/outputs), and architect decision trees.

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `EVALKIT_OPENAI_API_KEY` | One of these | OpenAI API key for GPT judges |
| `EVALKIT_ANTHROPIC_API_KEY` | required | Anthropic API key for Claude judges |
| `EVALKIT_CLERK_SECRET_KEY` | For auth | Clerk backend secret |
| `EVALKIT_CLERK_PUBLISHABLE_KEY` | For auth | Clerk frontend key |
| `EVALKIT_DB_PATH` | No | SQLite path (default: `./evalkit.db`) |
| `EVALKIT_DEFAULT_JUDGE` | No | Default judge model (default: `gpt-4o`) |

## License

[MIT License](LICENSE)
