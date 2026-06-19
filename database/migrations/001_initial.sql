-- ============================================================
-- PerX Challenge — Complete PostgreSQL Schema
-- Migration: 001_initial
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search on perks

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE user_role AS ENUM ('employee', 'employer', 'provider', 'admin');
CREATE TYPE perk_category AS ENUM ('fitness', 'travel', 'wellness', 'food', 'education', 'entertainment', 'transport', 'childcare', 'other');
CREATE TYPE selection_status AS ENUM ('pending_approval', 'approved', 'rejected', 'cancelled', 'expired');
CREATE TYPE interaction_type AS ENUM ('view', 'click', 'detail_open', 'add_to_wishlist', 'remove_from_wishlist', 'select', 'reject', 'redeem');
CREATE TYPE budget_period AS ENUM ('monthly', 'quarterly', 'annual', 'one_time');
CREATE TYPE provider_status AS ENUM ('pending_review', 'active', 'suspended', 'inactive');
CREATE TYPE notification_type AS ENUM ('selection_approved', 'selection_rejected', 'budget_low', 'new_perk', 'provider_update', 'system');

-- ============================================================
-- CORE AUTH TABLE
-- ============================================================

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) NOT NULL UNIQUE,
    hashed_password     VARCHAR(255) NOT NULL,
    role                user_role NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- PWA push notification subscription
    push_endpoint       TEXT,
    push_p256dh         TEXT,
    push_auth           TEXT,
    
    -- Preferences (ADR-007: Albania-first default locale)
    locale              VARCHAR(10) NOT NULL DEFAULT 'sq-AL',
    timezone            VARCHAR(50) NOT NULL DEFAULT 'UTC',
    
    -- Audit
    last_login_at       TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- EMPLOYER ORGANIZATION
-- ============================================================

CREATE TABLE employer_organizations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    organization_name   VARCHAR(255) NOT NULL,
    vat_number          VARCHAR(50),
    logo_url            TEXT,
    
    -- Contact
    contact_name        VARCHAR(255) NOT NULL,
    contact_phone       VARCHAR(50),
    
    -- Address
    address_line1       VARCHAR(255),
    address_city        VARCHAR(100),
    address_country     CHAR(2) NOT NULL DEFAULT 'IT',
    
    -- Platform settings
    default_monthly_budget_cents  INTEGER NOT NULL DEFAULT 0,  -- Per employee, minor units
    default_currency_code         VARCHAR(3) NOT NULL DEFAULT 'ALL',  -- ADR-007 ISO 4217
    require_approval    BOOLEAN NOT NULL DEFAULT TRUE,          -- Auto-approve if FALSE
    budget_period       budget_period NOT NULL DEFAULT 'monthly',
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- EMPLOYEE PROFILES
-- ============================================================

CREATE TABLE employee_profiles (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    employer_id                 UUID NOT NULL REFERENCES employer_organizations(id),
    
    -- Identity
    first_name                  VARCHAR(100) NOT NULL,
    last_name                   VARCHAR(100) NOT NULL,
    avatar_url                  TEXT,
    department                  VARCHAR(100),
    job_title                   VARCHAR(150),
    hire_date                   DATE,
    
    -- Onboarding (5-question form responses)
    onboarding_completed        BOOLEAN NOT NULL DEFAULT FALSE,
    lifestyle_tags              TEXT[] DEFAULT '{}',   -- ['cyclist', 'remote_worker', 'parent', ...]
    preferred_categories        perk_category[] DEFAULT '{}',
    budget_sensitivity          VARCHAR(20) DEFAULT 'medium',  -- 'low' | 'medium' | 'high'
    wellness_priority           INTEGER DEFAULT 5,   -- 1-10 scale
    family_situation            VARCHAR(20),         -- 'single' | 'couple' | 'family'
    
    -- Recommender state
    interaction_count           INTEGER NOT NULL DEFAULT 0,
    recommender_mode            VARCHAR(20) NOT NULL DEFAULT 'cold_start',  -- 'cold_start' | 'warm'
    affinity_vector             JSONB,  -- {fitness: 0.7, travel: 0.2, ...} — also cached in Redis
    affinity_updated_at         TIMESTAMP WITH TIME ZONE,
    
    -- LLM explanation (generated async)
    welcome_explanation         TEXT,   -- AI-generated welcome message
    
    created_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_employee_employer ON employee_profiles(employer_id);
CREATE INDEX idx_employee_mode ON employee_profiles(recommender_mode);
CREATE INDEX idx_employee_onboarding ON employee_profiles(onboarding_completed);

-- ============================================================
-- PROVIDER PROFILES
-- ============================================================

CREATE TABLE provider_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    company_name        VARCHAR(255) NOT NULL,
    description         TEXT,
    logo_url            TEXT,
    website_url         TEXT,
    status              provider_status NOT NULL DEFAULT 'pending_review',
    
    -- Geographic availability
    available_countries CHAR(2)[] NOT NULL DEFAULT '{IT}',
    available_cities    TEXT[] DEFAULT '{}',
    is_nationwide       BOOLEAN NOT NULL DEFAULT FALSE,
    is_remote           BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Stats (denormalized for fast provider list rendering)
    avg_rating          NUMERIC(3,2) DEFAULT 0,
    total_redemptions   INTEGER NOT NULL DEFAULT 0,
    total_perks         INTEGER NOT NULL DEFAULT 0,
    
    -- Platform financials
    commission_rate     NUMERIC(5,2) NOT NULL DEFAULT 15.00,  -- Platform takes X%
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_provider_status ON provider_profiles(status);

-- ============================================================
-- PERKS (THE MARKETPLACE ITEMS)
-- ============================================================

CREATE TABLE perks (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id             UUID NOT NULL REFERENCES provider_profiles(id) ON DELETE CASCADE,
    
    -- Content
    name                    VARCHAR(255) NOT NULL,
    slug                    VARCHAR(255) NOT NULL UNIQUE,
    description             TEXT NOT NULL,
    short_description       VARCHAR(500),
    category                perk_category NOT NULL,
    tags                    TEXT[] DEFAULT '{}',        -- ['yoga', 'online', 'group', ...]
    image_url               TEXT,
    
    -- Pricing (integer minor units per currency_code — ADR-007)
    employee_price_cents    INTEGER NOT NULL,            -- What employee sees/pays from budget
    provider_cost_cents     INTEGER NOT NULL,            -- NEVER expose to employees
    currency_code           VARCHAR(3) NOT NULL DEFAULT 'ALL',
    
    -- Availability
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    max_monthly_per_employee INTEGER DEFAULT NULL,       -- NULL = unlimited
    stock_limit             INTEGER DEFAULT NULL,        -- NULL = unlimited
    available_from          DATE,
    available_until         DATE,
    
    -- Content attributes for content-based filtering
    intensity_level         INTEGER,        -- 1-5 (for fitness perks: how intense)
    time_commitment_hours   NUMERIC(5,2),   -- Hours per month
    is_digital              BOOLEAN NOT NULL DEFAULT FALSE,
    is_family_friendly      BOOLEAN NOT NULL DEFAULT TRUE,
    minimum_commitment_months INTEGER DEFAULT 1,
    
    -- Recommender signals (updated nightly)
    popularity_score        NUMERIC(10,6) DEFAULT 0,    -- Global demand signal
    quality_score           NUMERIC(10,6) DEFAULT 0,    -- Fulfillment * rating
    trend_score             NUMERIC(10,6) DEFAULT 0,    -- Velocity of recent interactions
    
    -- Full-text search vector
    search_vector           TSVECTOR,
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_perks_provider ON perks(provider_id);
CREATE INDEX idx_perks_category ON perks(category);
CREATE INDEX idx_perks_active ON perks(is_active);
CREATE INDEX idx_perks_price ON perks(employee_price_cents);
CREATE INDEX idx_perks_search ON perks USING GIN(search_vector);
CREATE INDEX idx_perks_tags ON perks USING GIN(tags);
CREATE INDEX idx_perks_slug ON perks(slug);

-- Auto-update search vector
CREATE OR REPLACE FUNCTION perks_search_vector_trigger() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.name, '') || ' ' ||
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER perks_search_vector_update
    BEFORE INSERT OR UPDATE ON perks
    FOR EACH ROW EXECUTE FUNCTION perks_search_vector_trigger();

-- ============================================================
-- PACKAGES (ADR-007 — multi-provider bundles)
-- ============================================================

CREATE TABLE packages (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    category            VARCHAR(50),
    is_curated          BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    total_price_cents   INTEGER NOT NULL,
    currency_code       VARCHAR(3) NOT NULL DEFAULT 'ALL',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_packages_active ON packages(is_active);
CREATE INDEX idx_packages_category ON packages(category);
CREATE INDEX idx_packages_created_by ON packages(created_by_user_id);

CREATE TABLE package_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_id      UUID NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    perk_id         UUID NOT NULL REFERENCES perks(id) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (package_id, perk_id)
);

CREATE INDEX idx_package_items_package ON package_items(package_id);
CREATE INDEX idx_package_items_perk ON package_items(perk_id);

-- ============================================================
-- BUDGET LEDGER
-- ============================================================

CREATE TABLE budget_allocations (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employer_id             UUID NOT NULL REFERENCES employer_organizations(id),
    employee_id             UUID NOT NULL REFERENCES employee_profiles(id),
    
    period_year             SMALLINT NOT NULL,
    period_month            SMALLINT NOT NULL,           -- 1-12 (for monthly budgets)
    
    allocated_cents         INTEGER NOT NULL,            -- Total budget for this period
    spent_cents             INTEGER NOT NULL DEFAULT 0,  -- Sum of approved selections
    pending_cents           INTEGER NOT NULL DEFAULT 0,  -- Sum of pending selections
    currency_code           VARCHAR(3) NOT NULL DEFAULT 'ALL',  -- ADR-007
    
    -- Derived (updated by trigger or background job)
    remaining_cents         INTEGER GENERATED ALWAYS AS (allocated_cents - spent_cents - pending_cents) STORED,
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(employer_id, employee_id, period_year, period_month)
);

CREATE INDEX idx_budget_employee_period ON budget_allocations(employee_id, period_year, period_month);
CREATE INDEX idx_budget_employer ON budget_allocations(employer_id);

-- ============================================================
-- PERK SELECTIONS (THE MARKETPLACE TRANSACTION)
-- ============================================================

CREATE TABLE perk_selections (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id             UUID NOT NULL REFERENCES employee_profiles(id),
    perk_id                 UUID NOT NULL REFERENCES perks(id),
    employer_id             UUID NOT NULL REFERENCES employer_organizations(id),
    budget_allocation_id    UUID NOT NULL REFERENCES budget_allocations(id),
    package_id              UUID REFERENCES packages(id) ON DELETE SET NULL,  -- ADR-007
    
    status                  selection_status NOT NULL DEFAULT 'pending_approval',
    
    -- Price snapshot at time of selection (never recalculate from perk table)
    price_cents_snapshot    INTEGER NOT NULL,
    currency_code           VARCHAR(3) NOT NULL DEFAULT 'ALL',  -- ADR-007
    
    -- Approval workflow
    approved_by             UUID REFERENCES users(id),
    approved_at             TIMESTAMP WITH TIME ZONE,
    rejection_reason        TEXT,
    
    -- Redemption
    redeemed_at             TIMESTAMP WITH TIME ZONE,
    redemption_code         VARCHAR(100),
    
    -- Optimizer metadata
    was_optimized           BOOLEAN NOT NULL DEFAULT FALSE,     -- Did this come from plan_optimize?
    optimization_run_id     UUID,                               -- Links to optimizer_runs if applicable
    
    -- Recommender feedback signal
    was_recommended         BOOLEAN NOT NULL DEFAULT FALSE,
    recommendation_rank     INTEGER,                            -- What rank was this perk in the recommendation list?
    
    selected_at             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_selections_employee ON perk_selections(employee_id);
CREATE INDEX idx_selections_employer ON perk_selections(employer_id);
CREATE INDEX idx_selections_status ON perk_selections(status);
CREATE INDEX idx_selections_perk ON perk_selections(perk_id);
CREATE INDEX idx_selections_period ON perk_selections(employee_id, selected_at);
CREATE INDEX idx_selections_package ON perk_selections(package_id);

-- ============================================================
-- PAYMENTS (ADR-007 — simulated payout audit trail)
-- ============================================================

CREATE TABLE payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    perk_selection_id   UUID NOT NULL REFERENCES perk_selections(id) ON DELETE RESTRICT,
    provider_id         UUID NOT NULL REFERENCES provider_profiles(id) ON DELETE RESTRICT,
    employer_id         UUID NOT NULL REFERENCES employer_organizations(id) ON DELETE RESTRICT,
    amount_cents        INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency_code       VARCHAR(3) NOT NULL DEFAULT 'ALL',
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'completed', 'failed')),
    simulated           BOOLEAN NOT NULL DEFAULT TRUE,
    processed_at        TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_selection ON payments(perk_selection_id);
CREATE INDEX idx_payments_provider ON payments(provider_id);
CREATE INDEX idx_payments_employer ON payments(employer_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created ON payments(created_at);

-- ============================================================
-- INTERACTION LOG (RECOMMENDER TRAINING DATA)
-- ============================================================

CREATE TABLE perk_interactions (
    id                  BIGSERIAL PRIMARY KEY,   -- High volume: use serial not UUID
    employee_id         UUID NOT NULL REFERENCES employee_profiles(id),
    perk_id             UUID NOT NULL REFERENCES perks(id),
    
    interaction_type    interaction_type NOT NULL,
    
    -- Context at time of interaction
    recommendation_rank INTEGER,                 -- NULL if not from recommendation
    page_context        VARCHAR(50),             -- 'home', 'category', 'search', 'employer_featured'
    session_id          VARCHAR(100),
    
    -- Device context
    device_type         VARCHAR(20),             -- 'mobile', 'desktop', 'tablet'
    is_offline          BOOLEAN NOT NULL DEFAULT FALSE,  -- Was this action queued offline?
    
    occurred_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interactions_employee ON perk_interactions(employee_id);
CREATE INDEX idx_interactions_perk ON perk_interactions(perk_id);
CREATE INDEX idx_interactions_type ON perk_interactions(interaction_type);
CREATE INDEX idx_interactions_time ON perk_interactions(occurred_at);
-- Partial index for recommender training queries
CREATE INDEX idx_interactions_select_reject ON perk_interactions(employee_id, perk_id, occurred_at)
    WHERE interaction_type IN ('select', 'reject');

-- Trigger to update employee interaction_count and switch mode
CREATE OR REPLACE FUNCTION update_employee_interaction_count() RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    warm_threshold INTEGER;
BEGIN
    -- Only count explicit signals, not passive views
    IF NEW.interaction_type NOT IN ('select', 'reject', 'add_to_wishlist', 'redeem') THEN
        RETURN NEW;
    END IF;
    
    warm_threshold := COALESCE(
        (SELECT current_setting('app.recommender_warm_threshold', TRUE))::INTEGER,
        10
    );
    
    UPDATE employee_profiles
    SET 
        interaction_count = interaction_count + 1,
        recommender_mode = CASE 
            WHEN (interaction_count + 1) >= warm_threshold THEN 'warm'
            ELSE recommender_mode
        END,
        updated_at = NOW()
    WHERE id = NEW.employee_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER interactions_update_employee_mode
    AFTER INSERT ON perk_interactions
    FOR EACH ROW EXECUTE FUNCTION update_employee_interaction_count();

-- ============================================================
-- OPTIMIZER RUNS (AUDIT TRAIL FOR KNAPSACK)
-- ============================================================

CREATE TABLE optimizer_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id         UUID NOT NULL REFERENCES employee_profiles(id),
    
    -- Input
    wishlist_perk_ids   UUID[] NOT NULL,
    wishlist_scores     JSONB NOT NULL,          -- {perk_id: score, ...}
    budget_available_cents INTEGER NOT NULL,
    
    -- Output
    approved_perk_ids   UUID[],
    excluded_perk_ids   UUID[],
    total_cost_cents    INTEGER,
    total_score         NUMERIC(10,6),
    
    -- Performance
    solver_status       VARCHAR(50),             -- 'optimal', 'feasible', 'infeasible', 'timeout'
    solver_time_ms      INTEGER,
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- PROVIDER RATINGS
-- ============================================================

CREATE TABLE provider_ratings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employee_profiles(id),
    provider_id     UUID NOT NULL REFERENCES provider_profiles(id),
    perk_id         UUID NOT NULL REFERENCES perks(id),
    selection_id    UUID NOT NULL REFERENCES perk_selections(id),
    
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT,
    
    rated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(employee_id, selection_id)  -- One rating per selection
);

CREATE INDEX idx_ratings_provider ON provider_ratings(provider_id);
CREATE INDEX idx_ratings_perk ON provider_ratings(perk_id);

-- Auto-update provider avg_rating denormalized column
CREATE OR REPLACE FUNCTION update_provider_rating() RETURNS TRIGGER AS $$
BEGIN
    UPDATE provider_profiles
    SET avg_rating = (
        SELECT AVG(rating)::NUMERIC(3,2) FROM provider_ratings WHERE provider_id = NEW.provider_id
    )
    WHERE id = NEW.provider_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ratings_update_provider
    AFTER INSERT OR UPDATE ON provider_ratings
    FOR EACH ROW EXECUTE FUNCTION update_provider_rating();

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    type            notification_type NOT NULL,
    title           VARCHAR(255) NOT NULL,
    body            TEXT NOT NULL,
    data            JSONB DEFAULT '{}',          -- Extra payload for deep linking
    
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    push_sent       BOOLEAN NOT NULL DEFAULT FALSE,
    push_sent_at    TIMESTAMP WITH TIME ZONE,
    
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read)
    WHERE is_read = FALSE;

-- ============================================================
-- WISHLIST (pre-optimization)
-- ============================================================

CREATE TABLE employee_wishlists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL REFERENCES employee_profiles(id),
    perk_id         UUID NOT NULL REFERENCES perks(id),
    added_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(employee_id, perk_id)
);

-- ============================================================
-- REFRESH TOKENS
-- ============================================================

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,   -- bcrypt hash of the token
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_token ON refresh_tokens(token_hash);

-- ============================================================
-- UPDATED_AT TRIGGER (apply to all tables)
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'users', 'employer_organizations', 'employee_profiles',
        'provider_profiles', 'perks', 'budget_allocations',
        'perk_selections'
    ]) LOOP
        EXECUTE format('
            CREATE TRIGGER set_updated_at_%s
            BEFORE UPDATE ON %s
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        ', t, t);
    END LOOP;
END;
$$;
