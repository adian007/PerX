# ADR-001: Three-Sided Marketplace Data Model

**Status:** Accepted  
**Date:** 2025-06  
**Deciders:** Full team

---

## Context

PerX has three distinct actor types with fundamentally different data needs and access patterns:

- **Employees** need personalized recommendations, must see their remaining budget, and select/browse perks.
- **Employers** manage budgets per employee (or per department), approve/reject employee perk selections, and view aggregate analytics.
- **Providers** list their services (perks), set pricing, and view redemption/demand data for their offerings.

These actors intersect in the `perk_selections` (the marketplace transaction) and `budgets` (the financial contract) tables.

The core tension: should we use a single `users` table with a `role` discriminator, or separate `employees`, `employers`, `providers` tables with independent auth?

---

## Decision

**Use a single `users` table with role-discriminated extension tables.**

Core auth identity lives in `users`. Domain-specific attributes live in `employee_profiles`, `employer_organizations`, and `provider_profiles`. This is the "table inheritance" pattern (one level, not recursive).

---

## Options Considered

### Option A: Single `users` table + role field (flat)

| Dimension | Assessment |
|-----------|-----------|
| Complexity | Low |
| Schema size | Small (one table) |
| Query simplicity | High |
| Data isolation | Low (all columns for all roles in one table) |

**Pros:** Trivial auth queries. No JOINs for user lookup.  
**Cons:** Sparse rows (employee columns NULL for providers, etc.). Gets unmanageable past 20 columns. No natural FK constraints between domain entities.

### Option B: Three separate auth tables (no `users` table)

| Dimension | Assessment |
|-----------|-----------|
| Complexity | Medium |
| Schema size | Medium (3 auth tables) |
| Query simplicity | Low (auth middleware must try 3 tables) |
| Data isolation | High |

**Pros:** Complete separation.  
**Cons:** JWT must encode which table to look up. Shared features (push subscriptions, preferences) duplicate across tables.

### Option C: `users` table + extension tables (CHOSEN)

| Dimension | Assessment |
|-----------|-----------|
| Complexity | Medium |
| Schema size | Medium |
| Query simplicity | Medium (1 JOIN for domain data) |
| Data isolation | High |

**Pros:** Single auth lookup. Role-specific attributes stay in their own tables. Referential integrity via FK. Shared columns (email, hashed_password, role, push_token) stay in `users`.  
**Cons:** One extra JOIN per domain query. Slightly more complex migrations when adding role-specific fields.

---

## Trade-off Analysis

Option C wins because auth middleware only ever touches `users`. The extension tables are only accessed inside domain-specific service code. This mirrors Django's `AbstractUser` pattern and is battle-tested.

---

## Consequences

- Auth middleware queries `users` only — fast single-table lookup by `id` or `email`.
- Service code does `SELECT * FROM users JOIN employee_profiles ON ...` when it needs employee-specific data.
- Adding a new actor type (e.g., "HR Manager" sub-role) is a new extension table, not a schema change to `users`.
- Role changes require updating both `users.role` and potentially moving records between extension tables — acceptable risk for this use case.

---

## Action Items

- [x] Design `users` schema with shared fields
- [x] Design `employee_profiles`, `employer_organizations`, `provider_profiles` extension schemas
- [ ] Implement Alembic migration for initial schema
- [ ] Implement auth middleware that reads role from JWT and validates against `users.role`
