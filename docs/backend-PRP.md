# PRP: PerX Backend — Complete Implementation Blueprint

## Context

PerX is a three-sided employee benefits marketplace. The backend is a FastAPI (Python 3.11) application with PostgreSQL + Redis. It serves three actor types (employees, employers, providers) with distinct auth scopes, manages a budget optimization engine, and hosts a two-mode hybrid recommendation system. All decisions are documented in `/ADRs/`.

## Goal

A fully functional FastAPI backend that: authenticates all three roles, serves personalized recommendations, enforces budget constraints, handles the approval workflow, and logs all interactions for the recommender — running in Docker Compose with one command.

---

## Research Findings

### Existing Patterns to Follow
- All schemas in `app/schemas/` use Pydantic v2 (`model_config = ConfigDict(from_attributes=True)`)
- All routes use `Annotated[AsyncSession, Depends(get_db)]` for DB sessions
- All services are injected via `Depends(get_X_service)` — never instantiated directly in routes
- Error responses use `raise HTTPException(status_code=..., detail={"code": "...", "message": "..."} )`
- Background tasks use `background_tasks: BackgroundTasks` parameter in route function signature

### Dependencies (exact versions)
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.2.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
httpx==0.27.0
redis[asyncio]==5.0.4
scikit-surprise==1.1.3
implicit==0.7.2
lightgbm==4.3.0
pulp==2.8.0
pywebpush==2.0.0
python-multipart==0.0.9
```

### Gotchas
- SQLAlchemy 2.0 async: use `await session.execute(select(...))` not `session.query()`. Access results with `.scalars().all()` or `.scalar_one_or_none()`.
- `scikit-surprise` is not async-friendly — run it in `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking the event loop.
- PuLP's default solver (CBC) must be installed via `apt-get install coinor-cbc` in Dockerfile.
- Ollama endpoint: `http://host.docker.internal:11434` from inside Docker (on Linux: use `extra_hosts: ["host.docker.internal:host-gateway"]` in docker-compose.yml).
- Redis `DECR` on budget can go below zero if two requests race. Use a Lua script for atomic check-and-decrement.
- JWT `jti` (JWT ID) is a UUID stored in the token and checked against a Redis revocation set on each request.

---

## Implementation Plan

### Step 1: Project Scaffold & Config
**What:** Create the directory structure, `pyproject.toml`, `requirements.txt`, FastAPI app factory, settings class.  
**Files:** `backend/app/main.py`, `backend/app/config.py`, `backend/requirements.txt`

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    DATABASE_URL: str = "postgresql+asyncpg://perx:perx@localhost:5432/perx"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "gemma2:2b"
    RECOMMENDER_WARM_THRESHOLD: int = 10
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "admin@perx.local"

settings = Settings()
```

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import create_tables
from app.routers import auth, employees, employers, providers, perks, recommendations, budget, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connection, warm Redis connection pool
    yield
    # Shutdown: cleanup

app = FastAPI(title="PerX API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for router in [auth.router, employees.router, employers.router, providers.router,
               perks.router, recommendations.router, budget.router, analytics.router]:
    app.include_router(router, prefix="/api/v1")
```

**Validation:** `uvicorn app.main:app --reload` starts with no errors. `GET /docs` returns Swagger UI.

---

### Step 2: Database Layer
**What:** SQLAlchemy async engine, session factory, ORM models, Alembic migration.  
**Files:** `app/database.py`, `app/models/*.py`, `alembic/versions/001_initial.py`

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

ORM models mirror the SQL schema exactly. Key: use `mapped_column()` syntax (SQLAlchemy 2.0 style), `Mapped[Optional[str]]` type hints.

```python
# app/models/user.py
import uuid
from sqlalchemy import String, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    employee = "employee"
    employer = "employer"
    provider = "provider"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # ... rest of fields
```

**Validation:** `alembic upgrade head` runs without errors. `psql -c "\dt"` shows all tables.

---

### Step 3: Auth System
**What:** JWT creation/validation, role middleware, password hashing, all auth endpoints.  
**Files:** `app/auth/jwt.py`, `app/auth/middleware.py`, `app/auth/dependencies.py`, `app/routers/auth.py`

```python
# app/auth/jwt.py
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uuid
from app.config import settings

def create_access_token(user_id: str, role: str) -> str:
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (token, jti)"""
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM), jti

async def verify_token(token: str, redis_client) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Invalid token")
    
    # Check revocation set in Redis
    jti = payload.get("jti")
    if await redis_client.sismember("revoked_jtis", jti):
        raise ValueError("Token revoked")
    
    return payload
```

```python
# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    try:
        payload = await verify_token(credentials.credentials, redis)
    except ValueError as e:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": str(e)})
    
    user = await db.scalar(select(User).where(User.id == payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={"code": "USER_NOT_FOUND"})
    return user

def require_role(*roles):
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Insufficient role"})
        return current_user
    return role_checker

# Usage in router:
# current_employee = Depends(require_role("employee"))
```

**Validation:** `POST /api/v1/auth/register` creates user. `POST /api/v1/auth/login` returns JWT. Protected route with wrong role returns 403.

---

### Step 4: Redis Utilities
**What:** Async Redis client, budget cache helpers, atomic budget check-and-decrement Lua script.  
**Files:** `app/utils/redis.py`

```python
# app/utils/redis.py
import redis.asyncio as aioredis
from app.config import settings

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client

# Atomic check-and-decrement (Lua script prevents race conditions)
BUDGET_DECREMENT_SCRIPT = """
local key = KEYS[1]
local amount = tonumber(ARGV[1])
local current = tonumber(redis.call('GET', key))
if current == nil then
    return -2  -- Key not found, fall through to Postgres
end
if current < amount then
    return -1  -- Insufficient budget
end
redis.call('DECRBY', key, amount)
return current - amount  -- New balance
"""

async def atomic_budget_decrement(redis, employer_id: str, employee_id: str, period: str, amount_cents: int) -> int:
    """
    Returns: new balance (>=0), -1 if insufficient, -2 if key not found.
    """
    key = f"budget:{employer_id}:{employee_id}:{period}"
    result = await redis.eval(BUDGET_DECREMENT_SCRIPT, 1, key, amount_cents)
    return int(result)

async def get_or_set_budget_cache(redis, employer_id: str, employee_id: str, period: str, 
                                    fallback_fn) -> int:
    """Get budget from Redis or compute from Postgres and cache it."""
    key = f"budget:{employer_id}:{employee_id}:{period}"
    val = await redis.get(key)
    if val is not None:
        return int(val)
    
    # Fallback to Postgres
    balance = await fallback_fn()
    await redis.set(key, balance, ex=86400)  # 24h TTL
    return balance
```

**Validation:** Lua script handles concurrent requests without race condition (test with `asyncio.gather` of 10 simultaneous decrements against a budget of 5 items).

---

### Step 5: Recommendation Engine — Cold Start
**What:** Rules-based affinity engine (instant), async Ollama wrapper (non-blocking).  
**Files:** `app/services/recommendation/cold_start.py`, `app/utils/ollama.py`

```python
# app/services/recommendation/cold_start.py
from typing import Dict

CATEGORY_WEIGHTS = {
    # Format: lifestyle_tag → {category: weight_contribution}
    "cyclist": {"transport": 0.4, "fitness": 0.2},
    "remote_worker": {"education": 0.2, "wellness": 0.2, "food": 0.15},
    "parent": {"childcare": 0.5, "education": 0.2, "entertainment": 0.15},
    "gym_goer": {"fitness": 0.5},
    "foodie": {"food": 0.5},
    "traveler": {"travel": 0.6},
    "reader": {"education": 0.3, "entertainment": 0.2},
    "yogi": {"wellness": 0.5, "fitness": 0.2},
}

BUDGET_SENSITIVITY_MULTIPLIER = {"low": 0.7, "medium": 1.0, "high": 1.3}
WELLNESS_WEIGHT = 0.08  # Each point of wellness_priority (1-10) adds this much

def compute_affinity_vector(
    lifestyle_tags: list[str],
    preferred_categories: list[str],
    budget_sensitivity: str,
    wellness_priority: int,
    family_situation: str,
) -> Dict[str, float]:
    """
    Pure deterministic function. Same input → same output. No ML, no LLM.
    Returns affinity vector normalized to [0, 1] per category.
    """
    categories = ["fitness", "travel", "wellness", "food", "education", 
                  "entertainment", "transport", "childcare", "other"]
    scores = {c: 0.0 for c in categories}
    
    # Lifestyle tags
    for tag in lifestyle_tags:
        if tag in CATEGORY_WEIGHTS:
            for cat, weight in CATEGORY_WEIGHTS[tag].items():
                scores[cat] = min(1.0, scores[cat] + weight)
    
    # Explicit category preferences (direct boost)
    for cat in preferred_categories:
        if cat in scores:
            scores[cat] = min(1.0, scores[cat] + 0.3)
    
    # Wellness priority
    scores["wellness"] = min(1.0, scores["wellness"] + wellness_priority * WELLNESS_WEIGHT)
    
    # Family situation
    if family_situation == "family":
        scores["childcare"] = min(1.0, scores["childcare"] + 0.3)
        scores["entertainment"] = min(1.0, scores["entertainment"] + 0.15)
    
    # Apply budget sensitivity (affects willingness to spend on premium perks — stored separately)
    # budget_multiplier is stored on the profile, not in affinity vector
    
    # Normalize: ensure no category is 0 (minimum floor 0.05)
    for cat in scores:
        scores[cat] = max(0.05, scores[cat])
    
    return scores


async def get_cold_start_recommendations(
    affinity_vector: Dict[str, float],
    available_perks: list,  # List of Perk ORM objects
    budget_remaining_cents: int,
    limit: int = 20,
) -> list:
    """
    Score all perks using dot-product similarity with affinity vector.
    Filter to affordable perks (≤ remaining budget).
    """
    scored = []
    for perk in available_perks:
        if not perk.is_active:
            continue
        category_score = affinity_vector.get(perk.category.value, 0.05)
        # Factor in perk quality signals
        quality = perk.quality_score or 0.5
        price_factor = 1.0 if perk.employee_price_cents <= budget_remaining_cents else 0.1
        
        final_score = 0.5 * category_score + 0.3 * quality + 0.2 * perk.popularity_score
        final_score *= price_factor
        
        reason_code = f"AFFINITY_{perk.category.value.upper()}"
        scored.append((perk, final_score, reason_code))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
```

```python
# app/utils/ollama.py
import httpx
from app.config import settings

async def generate_recommendation_explanation(
    affinity_vector: dict,
    top_categories: list[str],
    employee_name: str,
) -> str | None:
    """
    Non-blocking LLM call. Returns None on failure.
    Always called inside BackgroundTasks.
    """
    prompt = f"""You are a friendly HR assistant for a benefits marketplace.
An employee named {employee_name} has these benefit preferences (scored 0-1):
{', '.join(f'{k}: {v:.2f}' for k, v in affinity_vector.items())}

Their top categories are: {', '.join(top_categories)}.

Write a 2-3 sentence personalized explanation of why these benefit categories were chosen for them.
Be warm, specific, and concise. Do NOT use generic phrases like "based on your data".
Focus on their lifestyle and what they'll gain."""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            response.raise_for_status()
            return response.json()["response"].strip()
    except Exception:
        # Silent failure — deterministic fallback used by caller
        return None

def get_fallback_explanation(top_category: str, employee_name: str) -> str:
    FALLBACKS = {
        "fitness": f"We prioritized fitness benefits for you, {employee_name}, to support an active, energized lifestyle.",
        "wellness": f"Your benefits focus on wellness, {employee_name} — giving you tools to recharge and stay balanced.",
        "food": f"We've highlighted food benefits for you, {employee_name}, from healthy meal kits to restaurant perks.",
        "travel": f"Travel perks take center stage in your recommendations, {employee_name} — explore more for less.",
        "education": f"Learning opportunities are front and center for you, {employee_name} — grow your skills on the company.",
    }
    return FALLBACKS.get(top_category, f"Welcome to PerX, {employee_name}! Your personalized benefits are ready.")
```

**Validation:** `compute_affinity_vector(["cyclist", "yogi"], ["fitness"], "medium", 8, "couple")` returns deterministic dict with fitness>0.6, wellness>0.6.

---

### Step 6: Recommendation Engine — Warm Mode (Hybrid)
**What:** Collaborative filtering via `implicit` library, UCB bandit, score combination.  
**Files:** `app/services/recommendation/hybrid.py`, `app/services/recommendation/bandits.py`

```python
# app/services/recommendation/hybrid.py
import asyncio
import numpy as np
from implicit.als import AlternatingLeastSquares
import scipy.sparse as sp

async def compute_warm_recommendations(
    employee_id: str,
    affinity_vector: dict,
    perk_df,          # DataFrame: columns [perk_id, category, tags, quality_score, popularity_score]
    interaction_matrix,  # scipy.sparse.csr_matrix: employees × perks
    employee_idx: int,
    perk_idx_to_id: dict,
    budget_remaining_cents: int,
    ucb_counts: dict,    # {perk_id: N} times perk was shown to this employee
    limit: int = 20,
) -> list:
    """
    Three-component scoring:
    final_score = 0.4 * content_score + 0.4 * cf_score + 0.2 * ucb_bonus
    """
    loop = asyncio.get_event_loop()
    
    # Component 1: Content-based (affinity dot product, instant)
    def content_score(perk_row) -> float:
        return affinity_vector.get(perk_row["category"], 0.05)
    
    # Component 2: Collaborative Filtering (ALS, run in executor)
    def run_als():
        model = AlternatingLeastSquares(factors=50, iterations=15, regularization=0.01)
        model.fit(interaction_matrix)
        scores, perk_indices = model.recommend(
            employee_idx, interaction_matrix[employee_idx], N=len(perk_df), filter_already_liked_items=False
        )
        return {perk_idx_to_id[perk_indices[i]]: float(scores[i]) for i in range(len(scores))}
    
    cf_scores = await loop.run_in_executor(None, run_als)
    
    # Component 3: UCB bonus (Upper Confidence Bound exploration)
    total_interactions = sum(ucb_counts.values()) or 1
    
    def ucb_bonus(perk_id: str) -> float:
        n = ucb_counts.get(perk_id, 0)
        if n == 0:
            return 1.0  # Never shown = maximum exploration bonus
        return min(1.0, np.sqrt(2 * np.log(total_interactions) / n))
    
    # Combine scores
    scored = []
    for _, perk_row in perk_df.iterrows():
        perk_id = perk_row["perk_id"]
        c_score = content_score(perk_row)
        cf_score = cf_scores.get(perk_id, 0.0)
        ucb = ucb_bonus(perk_id)
        final = 0.4 * c_score + 0.4 * cf_score + 0.2 * ucb
        
        # Penalize perks over budget
        if perk_row["employee_price_cents"] > budget_remaining_cents:
            final *= 0.1
        
        scored.append((perk_id, final, "HYBRID"))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
```

**Validation:** With a seeded interaction matrix, top-ranked items for an employee with high fitness interactions should be fitness perks. UCB bonus ensures variety.

---

### Step 7: Budget Optimizer (Knapsack)
**What:** PuLP 0/1 Knapsack for plan_optimize path.  
**Files:** `app/services/optimizer/knapsack.py`

```python
# app/services/optimizer/knapsack.py
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus, value, PULP_CBC_CMD
import time

def solve_knapsack(
    perks: list[dict],   # [{"id": uuid, "price_cents": int, "score": float, "name": str}]
    budget_cents: int,
    timeout_seconds: int = 5,
) -> dict:
    """
    0/1 Knapsack via PuLP CBC solver.
    
    Returns {
        "status": "optimal"|"feasible"|"infeasible",
        "approved_ids": [...],
        "excluded_ids": [...],
        "total_cost_cents": int,
        "total_score": float,
        "solver_time_ms": int,
    }
    """
    start = time.time()
    
    if not perks:
        return {"status": "infeasible", "approved_ids": [], "excluded_ids": [], 
                "total_cost_cents": 0, "total_score": 0.0, "solver_time_ms": 0}
    
    prob = LpProblem("perk_knapsack", LpMaximize)
    
    # Binary decision variables: x[i] = 1 if perk i is included
    x = {p["id"]: LpVariable(f"x_{i}", cat="Binary") for i, p in enumerate(perks)}
    
    # Objective: maximize total recommendation score
    prob += lpSum(p["score"] * x[p["id"]] for p in perks)
    
    # Constraint: total cost ≤ budget
    prob += lpSum(p["price_cents"] * x[p["id"]] for p in perks) <= budget_cents
    
    # Solve (CBC with time limit)
    solver = PULP_CBC_CMD(msg=0, timeLimit=timeout_seconds)
    prob.solve(solver)
    
    solver_ms = int((time.time() - start) * 1000)
    status = LpStatus[prob.status]
    
    approved_ids = [p["id"] for p in perks if value(x[p["id"]]) is not None and value(x[p["id"]]) > 0.5]
    excluded_ids = [p["id"] for p in perks if p["id"] not in approved_ids]
    
    return {
        "status": status.lower() if status in ("Optimal", "Feasible") else "infeasible",
        "approved_ids": approved_ids,
        "excluded_ids": excluded_ids,
        "total_cost_cents": sum(p["price_cents"] for p in perks if p["id"] in approved_ids),
        "total_score": sum(p["score"] for p in perks if p["id"] in approved_ids),
        "solver_time_ms": solver_ms,
    }
```

**Validation:** `solve_knapsack([{"id":1, "price_cents":3000, "score":0.9}, {"id":2, "price_cents":4000, "score":0.7}, {"id":3, "price_cents":2000, "score":0.8}], budget_cents=5000)` → approves items 1 and 3 (total 5000, score 1.7) not item 2.

---

### Step 8: Notification Service
**What:** Push notification via pywebpush, in-DB notification creation.  
**Files:** `app/services/notifications.py`

```python
# app/services/notifications.py
from pywebpush import webpush, WebPushException
import json

async def send_push_notification(
    subscription_info: dict,
    title: str,
    body: str,
    data: dict = None,
):
    """
    subscription_info = {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}
    Called inside BackgroundTasks — failures are logged but don't crash the request.
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({"title": title, "body": body, "data": data or {}}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"}
        )
    except WebPushException as e:
        # Log but don't raise — push failure must never fail the main request
        print(f"Push notification failed: {e}")

async def create_notification(db: AsyncSession, user_id: str, type: str, title: str, body: str, data: dict = None):
    """Create in-DB notification + optionally send push."""
    notification = Notification(user_id=user_id, type=type, title=title, body=body, data=data or {})
    db.add(notification)
    # Push is sent in background task by caller
```

---

### Step 9: Key Routers

**`app/routers/recommendations.py`** (pattern):
```python
@router.get("/recommendations")
async def get_recommendations(
    current_employee: Annotated[User, Depends(require_role("employee"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    limit: int = Query(20, le=50),
    category: Optional[str] = None,
    refresh: bool = False,
):
    # 1. Check Redis cache
    if not refresh:
        cached = await redis.get(f"recs:{current_employee.id}:scores")
        if cached:
            recs = json.loads(cached)
            return build_response(recs, mode="cached")
    
    # 2. Determine mode
    profile = await get_employee_profile(db, current_employee.id)
    
    if profile.recommender_mode == "cold_start":
        perks = await get_all_active_perks(db)
        budget = await get_budget_remaining(db, redis, profile)
        scored = await get_cold_start_recommendations(
            profile.affinity_vector, perks, budget.remaining_cents, limit
        )
    else:
        scored = await compute_warm_recommendations(...)  # hybrid engine
    
    # 3. Cache result
    await redis.setex(f"recs:{current_employee.id}:scores", 86400, json.dumps(serialize(scored)))
    
    return build_recommendation_response(scored, mode=profile.recommender_mode)
```

**`app/routers/budget.py`** (quick_add pattern):
```python
@router.post("/selections/quick-add")
async def quick_add_selection(
    body: QuickAddRequest,
    current_employee: Annotated[User, Depends(require_role("employee"))],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    perk = await get_active_perk_or_404(db, body.perk_id)
    profile = await get_employee_profile(db, current_employee.id)
    period = datetime.now().strftime("%Y-%m")
    
    # Atomic Redis check-and-decrement
    result = await atomic_budget_decrement(
        redis, str(profile.employer_id), str(profile.id), period, perk.employee_price_cents
    )
    
    if result == -2:
        # Redis miss — fallback to Postgres check
        result = await postgres_budget_check_and_reserve(db, profile, perk)
    
    if result == -1:
        raise HTTPException(400, {"code": "INSUFFICIENT_BUDGET", "message": "Not enough budget remaining."})
    
    # Write selection to Postgres
    selection = await create_selection(db, profile, perk)
    
    # Log interaction
    background_tasks.add_task(log_interaction, db, profile.id, perk.id, "select")
    
    # Notify employer if approval required
    if profile.employer.require_approval:
        background_tasks.add_task(notify_employer_new_selection, db, redis, selection)
    else:
        # Auto-approve
        await approve_selection(db, selection)
    
    return {"data": {
        "selection_id": str(selection.id),
        "status": selection.status.value,
        "budget_remaining_cents": result if result >= 0 else await get_budget_remaining_cents(db, profile),
    }}
```

**Validation:** Concurrent `quick_add` requests for an employee with €50 budget and two €30 perks → exactly one succeeds, one gets `INSUFFICIENT_BUDGET`.

---

### Step 10: Docker Compose
**Files:** `infra/docker-compose.yml`

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: perx
      POSTGRES_PASSWORD: perx
      POSTGRES_DB: perx
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./schema:/docker-entrypoint-initdb.d  # auto-run migrations
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U perx"]
      interval: 5s

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  api:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Ollama access on Linux
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app   # Hot reload in dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - api
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host

volumes:
  postgres_data:
  redis_data:
```

**Validation:** `docker compose up` → all services healthy. `curl localhost:8000/docs` returns 200. `curl localhost:5173` returns 200.

---

## Testing

```bash
# Unit tests (recommendation engine)
pytest tests/test_cold_start.py -v
pytest tests/test_knapsack.py -v

# Integration tests (API)
pytest tests/test_auth.py -v
pytest tests/test_selections.py -v  # includes concurrent budget test

# Load test (verify budget atomicity)
python tests/load_test_budget.py  # Custom: sends 20 concurrent quick_add requests
```

Passing looks like: all unit tests green, concurrent budget test shows exactly 1 success per available unit.

---

## Anti-Patterns

- **DO NOT** call `solve_knapsack()` from a `quick_add` endpoint — it adds 100-500ms latency unnecessarily.
- **DO NOT** put recommendation scoring in a router — it's 50+ lines of logic that belongs in `services/recommendation/`.
- **DO NOT** use `time.sleep()` anywhere — always `await asyncio.sleep()`.
- **DO NOT** load the ALS model on every request — train once, cache in memory, retrain nightly.
- **DO NOT** return `provider_cost_cents` in any employee-facing response — this is the platform's internal price.
- **DO NOT** trust client-provided `occurred_at` timestamps for security decisions, only for interaction log ordering.
