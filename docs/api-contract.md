# PerX API Contract — Complete Endpoint Reference

**Base URL:** `https://api.perx.local` (dev) | `https://api.perxchallenge.com` (prod)  
**Auth:** `Authorization: Bearer <access_token>` on all protected routes  
**Response envelope:** All responses: `{ "data": ..., "meta": { "timestamp": "...", "request_id": "..." } }`  
**Error envelope:** `{ "error": { "code": "SNAKE_CASE", "message": "...", "details": {} } }`  
**Pagination:** `?page=1&per_page=20` → meta includes `{ "total": N, "page": P, "per_page": PP, "pages": PP }`

---

## AUTH ROUTES (`/api/v1/auth`)

### POST /api/v1/auth/register
Register a new user. Role is determined by the registration endpoint (employees are invited, not self-registering in production — but for hackathon, allow all).

**Body:**
```json
{
  "email": "john@acme.com",
  "password": "strongpassword",
  "role": "employee",
  "employer_code": "ACME-XK92"   // Required if role=employee (invite code)
}
```
**Response 201:**
```json
{
  "data": {
    "user_id": "uuid",
    "role": "employee",
    "message": "Verify your email to continue."
  }
}
```
**Errors:** `EMAIL_ALREADY_EXISTS`, `INVALID_EMPLOYER_CODE`, `WEAK_PASSWORD`

---

### POST /api/v1/auth/login
**Body:**
```json
{ "email": "john@acme.com", "password": "..." }
```
**Response 200:**
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "john@acme.com",
      "role": "employee",
      "onboarding_completed": false
    }
  }
}
```
**Errors:** `INVALID_CREDENTIALS`, `ACCOUNT_INACTIVE`, `EMAIL_NOT_VERIFIED`

---

### POST /api/v1/auth/refresh
**Body:** `{ "refresh_token": "eyJ..." }`  
**Response 200:** Same as login but without `user`.  
**Errors:** `INVALID_REFRESH_TOKEN`, `TOKEN_EXPIRED`, `TOKEN_REVOKED`

---

### POST /api/v1/auth/logout
**Auth:** Required  
**Body:** `{ "refresh_token": "eyJ..." }`  
**Response 204:** Empty  

---

### POST /api/v1/auth/push-subscription
Register/update PWA push notification subscription.  
**Auth:** Required  
**Body:**
```json
{
  "endpoint": "https://fcm.googleapis.com/...",
  "keys": { "p256dh": "...", "auth": "..." }
}
```
**Response 200:** `{ "data": { "subscribed": true } }`

---

## EMPLOYEE ROUTES (`/api/v1/me` — requires role=employee)

### GET /api/v1/me
Get current employee's full profile.  
**Response 200:**
```json
{
  "data": {
    "id": "uuid",
    "email": "john@acme.com",
    "first_name": "John",
    "last_name": "Doe",
    "avatar_url": null,
    "department": "Engineering",
    "job_title": "Senior Developer",
    "onboarding_completed": false,
    "recommender_mode": "cold_start",
    "interaction_count": 3,
    "employer": {
      "id": "uuid",
      "organization_name": "Acme Corp",
      "logo_url": "..."
    }
  }
}
```

---

### POST /api/v1/me/onboarding
Complete the 5-question onboarding form. Triggers async LLM explanation generation.  
**Body:**
```json
{
  "lifestyle_tags": ["cyclist", "remote_worker"],
  "preferred_categories": ["fitness", "wellness", "food"],
  "budget_sensitivity": "medium",
  "wellness_priority": 8,
  "family_situation": "couple"
}
```
**Response 200:**
```json
{
  "data": {
    "onboarding_completed": true,
    "affinity_vector": {
      "fitness": 0.75,
      "travel": 0.15,
      "wellness": 0.80,
      "food": 0.55,
      "education": 0.30,
      "entertainment": 0.20,
      "transport": 0.60,
      "childcare": 0.10,
      "other": 0.10
    },
    "explanation_pending": true,   // LLM explanation generating async
    "explanation": null            // Will be populated when LLM completes
  }
}
```
**Side effects:** Fires background task → rules engine computes affinity vector → stores in Redis + Postgres → triggers async Ollama explanation → stores result in `employee_profiles.welcome_explanation`.

---

### GET /api/v1/me/onboarding/explanation
Poll for the async LLM explanation after onboarding.  
**Response 200:**
```json
{
  "data": {
    "ready": true,
    "explanation": "Based on your active lifestyle and cycling commute, we've prioritized fitness and transport benefits for you. Your focus on wellness means you'll see top options for yoga, meditation, and healthy food delivery."
  }
}
```

---

### GET /api/v1/me/budget
Get current month budget state.  
**Response 200:**
```json
{
  "data": {
    "period": "2025-06",
    "allocated_cents": 10000,
    "spent_cents": 3500,
    "pending_cents": 1500,
    "remaining_cents": 5000,
    "allocated_formatted": "€100.00",
    "spent_formatted": "€35.00",
    "pending_formatted": "€15.00",
    "remaining_formatted": "€50.00",
    "utilization_pct": 50.0
  }
}
```

---

### GET /api/v1/me/selections
Get all perk selections for the current employee.  
**Query params:** `?status=pending_approval&page=1&per_page=20`  
**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "status": "pending_approval",
      "perk": {
        "id": "uuid",
        "name": "Urban Bike Share Annual Pass",
        "category": "transport",
        "image_url": "...",
        "price_cents": 1500,
        "price_formatted": "€15.00"
      },
      "price_cents_snapshot": 1500,
      "selected_at": "2025-06-15T10:00:00Z",
      "approved_at": null,
      "rejection_reason": null
    }
  ],
  "meta": { "total": 3, "page": 1, "per_page": 20, "pages": 1, "timestamp": "..." }
}
```

---

### GET /api/v1/me/wishlist
Get employee's current wishlist.  
**Response 200:** List of perks with standard perk fields.

---

### POST /api/v1/me/wishlist/{perk_id}
Add perk to wishlist.  
**Response 201:** `{ "data": { "added": true, "perk_id": "uuid" } }`  
**Errors:** `PERK_NOT_FOUND`, `ALREADY_IN_WISHLIST`, `PERK_INACTIVE`

---

### DELETE /api/v1/me/wishlist/{perk_id}
Remove from wishlist.  
**Response 204:** Empty.

---

## RECOMMENDATION ROUTES (`/api/v1/recommendations` — requires role=employee)

### GET /api/v1/recommendations
Get personalized recommendations for the current employee.  
**Query params:** `?limit=20&category=fitness&refresh=false`  
- `refresh=true` forces recomputation (skips cache)  

**Response 200:**
```json
{
  "data": {
    "mode": "cold_start",
    "perks": [
      {
        "id": "uuid",
        "name": "Urban Yoga Studio — Monthly Pass",
        "category": "wellness",
        "short_description": "Unlimited classes at 50+ studios in your city.",
        "image_url": "...",
        "employee_price_cents": 4500,
        "employee_price_formatted": "€45.00",
        "provider": {
          "id": "uuid",
          "company_name": "FlowFit",
          "logo_url": "...",
          "avg_rating": 4.7
        },
        "recommendation_score": 0.847,
        "reason_code": "AFFINITY_WELLNESS_HIGH",
        "reason_text": "Matches your high wellness priority",
        "tags": ["yoga", "group_classes", "flexible"],
        "is_affordable": true,    // price ≤ 80% of remaining budget
        "is_featured": false
      }
    ],
    "total": 20,
    "cached": true,
    "cache_age_seconds": 3420
  }
}
```

---

### GET /api/v1/recommendations/categories
Get category-level affinity breakdown (for the globe visualization).  
**Response 200:**
```json
{
  "data": {
    "categories": [
      { "category": "fitness", "score": 0.75, "perk_count": 42, "color": "#FF6B35" },
      { "category": "wellness", "score": 0.80, "perk_count": 31, "color": "#4ECDC4" },
      { "category": "food", "score": 0.55, "perk_count": 67, "color": "#45B7D1" },
      { "category": "transport", "score": 0.60, "perk_count": 19, "color": "#96E6A1" },
      { "category": "education", "score": 0.30, "perk_count": 28, "color": "#DDA0DD" }
    ]
  }
}
```

---

## PERK SELECTION ROUTES

### POST /api/v1/selections/quick-add
Add a single perk immediately (fast path).  
**Body:**
```json
{ "perk_id": "uuid" }
```
**Response 200:**
```json
{
  "data": {
    "selection_id": "uuid",
    "status": "pending_approval",
    "budget_remaining_cents": 3500,
    "budget_remaining_formatted": "€35.00",
    "message": "Your selection is awaiting approval."
  }
}
```
**Errors:** `INSUFFICIENT_BUDGET`, `PERK_NOT_FOUND`, `PERK_INACTIVE`, `ALREADY_SELECTED_THIS_MONTH`, `BUDGET_PERIOD_CLOSED`

---

### POST /api/v1/selections/optimize-plan
Submit wishlist for knapsack optimization.  
**Body:**
```json
{
  "perk_ids": ["uuid1", "uuid2", "uuid3", "uuid4"]
}
```
**Response 200:**
```json
{
  "data": {
    "run_id": "uuid",
    "status": "optimal",
    "solver_time_ms": 127,
    "budget_available_cents": 5000,
    "approved_perks": [
      {
        "perk_id": "uuid1",
        "name": "Yoga Monthly Pass",
        "price_cents": 4500,
        "score": 0.847,
        "included": true
      },
      {
        "perk_id": "uuid2",
        "name": "Gym Membership",
        "price_cents": 8000,
        "score": 0.720,
        "included": false,
        "exclusion_reason": "Would exceed budget by €35.00"
      }
    ],
    "total_cost_cents": 4500,
    "total_score": 0.847,
    "explanation": "We selected 1 of 4 perks to maximize your benefit within the €50.00 budget."
  }
}
```

---

### POST /api/v1/selections/optimize-plan/{run_id}/confirm
Confirm and submit the optimized selection.  
**Body:** `{}` (empty — confirms the run_id output)  
**Response 201:** List of created `selection_id`s.

---

### DELETE /api/v1/selections/{selection_id}
Cancel a pending selection (before employer approval).  
**Response 204:** Empty.

---

## INTERACTION LOGGING

### POST /api/v1/interactions
Log a user interaction. Called by the frontend on every meaningful event.  
**Body:**
```json
{
  "perk_id": "uuid",
  "type": "view",
  "recommendation_rank": 3,
  "page_context": "home",
  "session_id": "sess_abc123",
  "occurred_at": "2025-06-15T10:05:00Z"   // Client timestamp (used for offline replay)
}
```
**Response 201:** `{ "data": { "logged": true } }`

### POST /api/v1/interactions/batch
Batch version for offline replay (Background Sync API sends accumulated events on reconnect).  
**Body:** `{ "events": [ ...array of single interaction bodies... ] }`  
**Response 201:** `{ "data": { "accepted": 12, "rejected": 0 } }`

---

## EMPLOYER ROUTES (`/api/v1/employer` — requires role=employer)

### GET /api/v1/employer/organization
Get organization profile and settings.

### PATCH /api/v1/employer/organization
Update settings (budget defaults, require_approval toggle).

### GET /api/v1/employer/employees
List all employees with budget summary.  
**Query params:** `?page=1&per_page=50&department=Engineering&search=john`  
**Response 200:** Array of employees with `{ id, name, budget_utilization_pct, pending_approvals_count, active_selections_count }`.

### POST /api/v1/employer/employees/invite
Send invitation to an employee.  
**Body:** `{ "email": "employee@acme.com", "department": "Engineering", "monthly_budget_cents": 10000 }`

### GET /api/v1/employer/budget/overview
Dashboard summary.  
**Response 200:**
```json
{
  "data": {
    "period": "2025-06",
    "total_employees": 45,
    "total_allocated_cents": 450000,
    "total_spent_cents": 178000,
    "total_pending_cents": 35000,
    "utilization_pct": 47.3,
    "top_categories": [
      { "category": "fitness", "spend_cents": 68000, "pct": 38.2 }
    ]
  }
}
```

### GET /api/v1/employer/approvals
Get pending approval queue.  
**Query params:** `?page=1&per_page=20`  
**Response 200:**
```json
{
  "data": [
    {
      "selection_id": "uuid",
      "employee": { "id": "uuid", "name": "John Doe", "department": "Engineering" },
      "perk": { "id": "uuid", "name": "Yoga Monthly Pass", "category": "wellness", "image_url": "..." },
      "price_cents": 4500,
      "budget_remaining_after_cents": 5500,
      "selected_at": "2025-06-15T10:00:00Z"
    }
  ]
}
```

### POST /api/v1/employer/approvals/{selection_id}/approve
**Response 200:** `{ "data": { "status": "approved", "notification_sent": true } }`  
**Side effects:** Updates `perk_selections.status`, updates budget ledger, sends push notification to employee.

### POST /api/v1/employer/approvals/{selection_id}/reject
**Body:** `{ "reason": "Not aligned with current benefit policy." }`  
**Response 200:** `{ "data": { "status": "rejected", "notification_sent": true } }`

### POST /api/v1/employer/approvals/bulk-approve
**Body:** `{ "selection_ids": ["uuid1", "uuid2"] }`  
**Response 200:** `{ "data": { "approved": 2, "failed": 0 } }`

### GET /api/v1/employer/analytics
Full analytics dashboard.  
**Query params:** `?period=2025-06`  
**Response:** Deep analytics object (top perks, category distribution, employee engagement, budget trend chart data).

---

## PROVIDER ROUTES (`/api/v1/provider` — requires role=provider)

### GET /api/v1/provider/profile
### PATCH /api/v1/provider/profile
### GET /api/v1/provider/perks — List own perks
### POST /api/v1/provider/perks — Create new perk
### PATCH /api/v1/provider/perks/{perk_id}
### DELETE /api/v1/provider/perks/{perk_id} — Soft delete (sets is_active=false)
### GET /api/v1/provider/analytics — Redemptions, ratings, demand by category

**POST /api/v1/provider/perks body:**
```json
{
  "name": "Urban Yoga Studio — Monthly Pass",
  "description": "Unlimited classes at 50+ partner studios.",
  "short_description": "Unlimited yoga, 50+ studios",
  "category": "wellness",
  "tags": ["yoga", "group_classes", "online_option"],
  "employee_price_cents": 4500,
  "provider_cost_cents": 3500,
  "image_url": "https://...",
  "is_digital": false,
  "is_family_friendly": true,
  "max_monthly_per_employee": 1,
  "minimum_commitment_months": 1,
  "time_commitment_hours": 4.0,
  "intensity_level": 3
}
```

---

## PERKS BROWSE ROUTES (public-ish — requires auth, any role)

### GET /api/v1/perks
Browse all active perks.  
**Query params:** `?category=wellness&min_price=0&max_price=5000&search=yoga&tags=online&page=1&per_page=20&sort=popularity`  
**Sorts:** `popularity`, `price_asc`, `price_desc`, `rating`, `newest`

### GET /api/v1/perks/{perk_id}
Get single perk detail. Fires `view` interaction log in background.

### GET /api/v1/perks/featured
Homepage featured perks (employer-curated + platform-featured).

---

## NOTIFICATIONS

### GET /api/v1/notifications — List user notifications
**Query params:** `?unread_only=true&page=1&per_page=20`

### POST /api/v1/notifications/{id}/read — Mark as read

### POST /api/v1/notifications/read-all — Mark all as read

---

## ADMIN ROUTES (`/api/v1/admin` — requires role=admin)

### GET /api/v1/admin/providers — List providers pending review
### POST /api/v1/admin/providers/{id}/approve
### POST /api/v1/admin/providers/{id}/suspend
### GET /api/v1/admin/stats — Platform-wide stats
### POST /api/v1/admin/recommender/retrain — Trigger model retraining job

---

## INTERNAL ROUTES (not authenticated, internal network only)

### POST /api/v1/internal/llm-callback
Receives the result from the async Ollama job.  
**Body:** `{ "employee_id": "uuid", "type": "welcome_explanation", "content": "...", "job_id": "..." }`  
**Response 200:** `{ "data": { "stored": true } }`

---

## WEBSOCKET (optional, demo enhancement)

`WS /api/v1/ws/employer/{employer_id}`  
Events pushed to employer dashboard:
- `{ "type": "new_selection", "data": { selection } }` — new approval needed
- `{ "type": "budget_update", "data": { employee_id, budget } }` — budget changed

`WS /api/v1/ws/employee/{employee_id}`  
Events pushed to employee:
- `{ "type": "selection_approved", "data": { selection_id, perk } }`
- `{ "type": "selection_rejected", "data": { selection_id, reason } }`
- `{ "type": "llm_ready", "data": { type, content } }` — explanation ready
