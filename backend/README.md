# PerX Recommendation Backend (slice)

FastAPI service implementing the PerX two-mode recommendation engine and async Ollama integration. This is the **recommendation slice** of the full PerX backend — DB, auth, and Redis are integration stubs until teammates wire them.

## Quick start

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
uvicorn app.main:app --reload
```

Open Swagger UI at `http://localhost:8000/docs`.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RECOMMENDER_WARM_THRESHOLD` | `10` | Interactions before warm mode |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `gemma2:2b` | Model name for explanations |
| `OLLAMA_TIMEOUT_SECONDS` | `5.0` | HTTP timeout for Ollama |
| `OLLAMA_FORCE_FAIL` | `false` | Force fallback explanations (demo/tests) |
| `OLLAMA_MAX_RETRIES` | `0` | Retries for Ollama generate calls |

## Demo API

### Recommendations

```bash
# Cold start (default)
curl "http://localhost:8000/api/v1/recommendations?demo=cold&limit=5"

# Warm hybrid with score breakdown
curl "http://localhost:8000/api/v1/recommendations?demo=warm&include_score_breakdown=true"

# Cache hit on second identical request
curl "http://localhost:8000/api/v1/recommendations?demo=warm"
curl "http://localhost:8000/api/v1/recommendations?demo=warm"   # cached: true

# Force recompute
curl "http://localhost:8000/api/v1/recommendations?demo=warm&refresh=true"
```

Demo profiles: `demo=new` | `demo=cold` | `demo=warm`. Legacy `warm_demo=true` maps to `demo=warm`.

### Onboarding

```bash
curl -X POST http://localhost:8000/api/v1/me/onboarding \
  -H "Content-Type: application/json" \
  -d '{
    "lifestyle_tags": ["cyclist", "yogi"],
    "preferred_categories": ["fitness", "wellness"],
    "budget_sensitivity": "medium",
    "wellness_priority": 8,
    "family_situation": "couple"
  }'

curl http://localhost:8000/api/v1/me/onboarding/explanation
```

### Diagnostics

```bash
curl http://localhost:8000/api/v1/internal/ollama-health
```

## ALS retrain script

```bash
python -m scripts.retrain_als
```

Reads `scripts/fixtures/interactions.json`, trains ALS via `implicit`, writes `scripts/output/cf_scores_by_employee.json`.

## Architecture

- **Cold start** (`interaction_count < threshold`): rules-based affinity from 5 onboarding fields
- **Warm** (`interaction_count >= threshold`): `0.4×content + 0.4×CF + 0.2×UCB`, budget penalty ×0.1
- **LLM**: always async via `BackgroundTasks`; template fallback when Ollama is down

### Integration entry point

Teammates call `build_recommendation_payload()` from `app/services/recommendation/engine.py` and map DB rows via `app/services/recommendation/mappers.py`. Swap `InMemoryRecommendationCache` for Redis using the `RecommendationCache` protocol in `cache.py`.

### Redis keys (ADR-006 — teammates implement)

- `recs:{employee_id}:scores` — precomputed recommendations (24h TTL)
- `affinity:{employee_id}` — affinity vector (30d TTL)

## Tests

```bash
pytest tests/ -v
```

Covers cold-start affinity, warm hybrid math, cache hit/miss, onboarding flow, and API envelopes.
