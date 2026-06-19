# ADR-002: Recommendation Engine Architecture

**Status:** Accepted  
**Date:** 2025-06

## Context

The recommender must handle two distinct phases: (1) a brand-new employee with zero interaction history (cold-start), and (2) a returning employee with interaction history (warm). These phases have completely different data availability and latency constraints.

## Decision

**Two-mode hybrid recommender with explicit mode switching at `interaction_count >= 10`.**

- Mode 0 (cold-start, `interaction_count < 10`): Rules-based affinity engine from 5-question onboarding form. LLM generates a human-readable explanation of the recommendation asynchronously.
- Mode 1 (warm, `interaction_count >= 10`): Hybrid scoring: `final_score = 0.4 * content_score + 0.4 * CF_score + 0.2 * UCB_bonus`. Scores are pre-computed nightly and stored in Redis for sub-50ms reads.

## Options Considered

### Option A: LLM-only (zero-shot, always)
**Pros:** Simplest code. No ML model management.  
**Cons:** 500ms-3s latency per recommendation. LLM failure = no recommendations. API cost at scale. Unacceptable for real-time UI.

### Option B: Pure collaborative filtering (matrix factorization)
**Pros:** Well-understood. Fast after training.  
**Cons:** Cold-start is a brick wall for new employees — produces garbage recommendations. CF alone ignores perk content attributes (category, tags, cost tier).

### Option C: Two-mode hybrid (CHOSEN)
**Pros:** Cold-start handled deterministically. LLM is additive, never blocking. ML model improves over time. Budget constraint always enforced server-side regardless of recommendation source.  
**Cons:** Two code paths to maintain. Mode-switching logic must be tested carefully.

## Trade-off Analysis

Option C is the only one that works at demo time (mostly cold-start users) AND continues to improve post-hackathon. The 10-interaction threshold is empirical and configurable via environment variable `RECOMMENDER_WARM_THRESHOLD`.

---

# ADR-003: LLM Integration Strategy

**Status:** Accepted  
**Date:** 2025-06

## Context

The system uses an LLM for two purposes: (1) cold-start preference inference, and (2) natural-language explanation of recommendations ("why you got this"). The risk is that LLM inference (Ollama, local) can be slow (1-5s) or fail entirely if the local server is down.

## Decision

**LLM is never in the synchronous request path. All LLM calls use FastAPI `BackgroundTasks`. Deterministic fallbacks exist for every LLM output.**

- Affinity vector: computed by rules engine instantly. LLM generates explanation text in background, POSTed to a `/internal/llm-callback` endpoint when complete.
- Recommendation explanation: generated async. UI shows a skeleton until it arrives via polling or WebSocket.
- If LLM is unreachable: use template strings keyed by top affinity category. Example: `"Based on your profile, we prioritized {top_category} benefits for you."`

## Consequences

- Demo works even if Ollama crashes.
- "AI explanation" is a progressive enhancement, not a dependency.
- Background task runner must have error logging — silent LLM failures are acceptable but must be observable.

---

# ADR-004: Budget Optimization — Two-Path Architecture

**Status:** Accepted  
**Date:** 2025-06

## Context

Employees interact with budget in two ways: (1) quick-adding a single perk they found browsing, and (2) building a wishlist that may exceed their budget and needs optimization to find the best subset. These have wildly different latency and computation requirements.

## Decision

**Two explicit paths: `quick_add` and `plan_optimize`.**

### Path 1: `quick_add` (single perk)
- Check: `Redis GET budget:{employer_id}:{employee_id}:{YYYY-MM}` → remaining balance ≥ perk.employee_price?
- If yes: DECREMENT Redis, write to Postgres `perk_selections`, return 200 in <50ms.
- Background: sync Redis → Postgres `budget_ledger` (reconciliation every 5 min or on session end).

### Path 2: `plan_optimize` (wishlist of N perks)
- Triggered when: employee submits a wishlist where `sum(prices) > remaining_budget`.
- Algorithm: 0/1 Knapsack via PuLP on `(item=perk, weight=employee_price, value=recommendation_score)`.
- Constraint: `sum(weights of selected) ≤ remaining_budget`.
- Output: approved subset of perks + explanation of what was excluded and why.
- Latency: 100-500ms acceptable (employee is reviewing a plan, not clicking fast).

## Consequences

- `quick_add` never blocks on PuLP — critical for UX.
- `plan_optimize` is the only place that calls PuLP — clear boundary.
- Budget state can temporarily diverge between Redis and Postgres during the 5-minute reconciliation window. This is acceptable: the worst case is an employee briefly over-budgeted by one perk, corrected on next reconciliation.
- Employer approval is a separate async step that doesn't block employee browsing.

---

# ADR-005: PWA vs Native App

**Status:** Accepted  
**Date:** 2025-06

## Context

PerX needs to be accessible on mobile (employees browse perks on their phones), support offline browsing, and deliver push notifications for approval events. The question is whether to build native iOS/Android apps or a Progressive Web App.

## Decision

**Build a PWA (Progressive Web App) using Vite PWA Plugin (Workbox). No native apps.**

## Options Considered

### Option A: React Native (cross-platform native)
| Dimension | Assessment |
|-----------|-----------|
| Build time | High (new codebase, new skills needed) |
| Push notifications | Excellent (native push) |
| Offline | Excellent (SQLite) |
| Team familiarity | Low (team knows React, not RN) |

### Option B: PWA (CHOSEN)
| Dimension | Assessment |
|-----------|-----------|
| Build time | Low (same React codebase) |
| Push notifications | Good on Android/Chrome, partial on iOS 16.4+ |
| Offline | Good (Workbox + Dexie.js) |
| Team familiarity | High |

### Option C: Responsive Web only (no PWA)
**Rejected**: No offline support, no push, can't be installed to home screen — loses key differentiators.

## Consequences

- iOS users: Push notifications only work in installed PWA (share → Add to Home Screen). Not available in Safari tab. Fallback: in-app polling at 30s intervals.
- Android: Full PWA capability including install prompt and push.
- Service Worker strategy: Cache-first for app shell. Network-first (with offline fallback) for `/api/recommendations` and `/api/perks`.
- IndexedDB schema (Dexie.js): `perks`, `recommendations`, `pending_actions` (offline queue).

---

# ADR-006: Database — PostgreSQL + Redis Dual Write

**Status:** Accepted  
**Date:** 2025-06

## Context

The system needs two things: a reliable source of truth for financial data (budget ledger, perk selections) and sub-50ms response times for budget checks and recommendation reads during normal browsing.

## Decision

**PostgreSQL 16 as source of truth. Redis 7 as write-through cache for budget state and pre-computed recommendation scores.**

## Redis Key Schema

```
# Budget remaining (write-through, TTL: end of month + 1 day)
budget:{employer_id}:{employee_id}:{YYYY-MM}   → FLOAT (remaining balance in EUR cents)

# Pre-computed recommendation scores (TTL: 24h)
recs:{employee_id}:scores                       → JSON list of {perk_id, score, reason_code}

# Affinity vector (TTL: 30 days)
affinity:{employee_id}                          → JSON {fitness: 0.7, travel: 0.2, ...}

# Session data (TTL: 15 min)
session:{access_token_jti}                      → JSON {user_id, role, exp}

# Rate limiting
ratelimit:{user_id}:{endpoint}                  → INCR counter (TTL: 1 min)
```

## Reconciliation

A background job runs every 5 minutes:
1. `SELECT employee_id, SUM(employee_price) FROM perk_selections WHERE month = current_month GROUP BY employee_id`
2. Compare against Redis values.
3. On mismatch: trust Postgres, update Redis.

## Consequences

- Redis failure: system degrades gracefully. Budget checks fall through to Postgres (100-300ms instead of <50ms). Recommendation scores fall through to on-demand computation (500ms-2s).
- Redis must NOT be the only record of a transaction. `perk_selections` Postgres write always happens, Redis is the cache.
