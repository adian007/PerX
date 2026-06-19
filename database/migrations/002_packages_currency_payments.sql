-- ============================================================
-- PerX Challenge — Migration 002
-- Multi-Provider Packages, Currency/Localization, Simulated Payments
--
-- NOTE: Fresh installs should use 001_initial.sql only (ADR-007 merged there).
-- Run this file only when upgrading a database created from pre-ADR-007 001_initial.sql.
--
-- Prerequisite: 001_initial.sql must be applied first.
-- Idempotent: safe to re-run when objects already exist.
--
-- Apply:
--   Get-Content database/migrations/002_packages_currency_payments.sql |
--     docker exec -i perx_postgres psql -U perx_user -d perx
--
-- Reference: docs/ADR-007.md
-- ============================================================

-- ============================================================
-- PART 1 — Currency & Localization
-- ============================================================

-- users.locale already exists in 001_initial (default 'en'); align default with ADR-007.
ALTER TABLE users
    ALTER COLUMN locale SET DEFAULT 'sq-AL';

COMMENT ON COLUMN users.locale IS
    'BCP-47 locale for number/date formatting (ADR-007). Default sq-AL for Albania-first demo.';

ALTER TABLE employer_organizations
    ADD COLUMN IF NOT EXISTS default_currency_code VARCHAR(3) NOT NULL DEFAULT 'ALL';

COMMENT ON COLUMN employer_organizations.default_currency_code IS
    'ISO 4217 currency for this employer org (ADR-007). No FX conversion in hackathon scope.';

ALTER TABLE perks
    ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NOT NULL DEFAULT 'ALL';

COMMENT ON COLUMN perks.employee_price_cents IS
    'Price in smallest currency unit for perks.currency_code (ADR-007). Column name kept as _cents.';

COMMENT ON COLUMN perks.provider_cost_cents IS
    'Platform cost to provider — NEVER expose in employee-facing APIs or Pydantic schemas.';

ALTER TABLE budget_allocations
    ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NOT NULL DEFAULT 'ALL';

ALTER TABLE perk_selections
    ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NOT NULL DEFAULT 'ALL';

-- ============================================================
-- PART 2 — Multi-Provider Packages
-- ============================================================

CREATE TABLE IF NOT EXISTS packages (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    category            VARCHAR(50),
    is_curated          BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id  UUID,
    total_price_cents   INTEGER NOT NULL,
    currency_code       VARCHAR(3) NOT NULL DEFAULT 'ALL',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE packages IS
    'Curated or employee-built bundles spanning one or more perks/providers (ADR-007).';

-- FK: packages.created_by_user_id → users
-- ON DELETE SET NULL — curated packages remain if the creating admin/user is removed.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_packages_created_by_user'
    ) THEN
        ALTER TABLE packages
            ADD CONSTRAINT fk_packages_created_by_user
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_packages_active ON packages(is_active);
CREATE INDEX IF NOT EXISTS idx_packages_category ON packages(category);
CREATE INDEX IF NOT EXISTS idx_packages_created_by ON packages(created_by_user_id);

CREATE TABLE IF NOT EXISTS package_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_id      UUID NOT NULL,
    perk_id         UUID NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (package_id, perk_id)
);

-- FK: package_items.package_id → packages
-- ON DELETE CASCADE — line items are owned by the package; delete with parent.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_package_items_package'
    ) THEN
        ALTER TABLE package_items
            ADD CONSTRAINT fk_package_items_package
            FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE;
    END IF;
END $$;

-- FK: package_items.perk_id → perks
-- ON DELETE RESTRICT — cannot delete a perk that is part of an active package definition.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_package_items_perk'
    ) THEN
        ALTER TABLE package_items
            ADD CONSTRAINT fk_package_items_perk
            FOREIGN KEY (perk_id) REFERENCES perks(id) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_package_items_package ON package_items(package_id);
CREATE INDEX IF NOT EXISTS idx_package_items_perk ON package_items(perk_id);

ALTER TABLE perk_selections
    ADD COLUMN IF NOT EXISTS package_id UUID;

-- FK: perk_selections.package_id → packages
-- ON DELETE SET NULL — preserve selection/payment audit history if a package is retired.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_perk_selections_package'
    ) THEN
        ALTER TABLE perk_selections
            ADD CONSTRAINT fk_perk_selections_package
            FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_selections_package ON perk_selections(package_id);

COMMENT ON COLUMN perk_selections.package_id IS
    'When set, selection is part of a package; employer approval can batch by package_id.';

-- ============================================================
-- PART 3 — Simulated Payments
-- ============================================================

CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    perk_selection_id   UUID NOT NULL,
    provider_id         UUID NOT NULL,
    employer_id         UUID NOT NULL,
    amount_cents        INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency_code       VARCHAR(3) NOT NULL DEFAULT 'ALL',
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'completed', 'failed')),
    simulated           BOOLEAN NOT NULL DEFAULT TRUE,
    processed_at        TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE payments IS
    'Simulated payment audit trail after selection approval (ADR-007). No real payment rail.';
COMMENT ON COLUMN payments.simulated IS
    'Always TRUE for hackathon; column allows future real payment integration without schema change.';

-- FK: payments.perk_selection_id → perk_selections
-- ON DELETE RESTRICT — financial audit trail must not orphan via selection deletion.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_payments_perk_selection'
    ) THEN
        ALTER TABLE payments
            ADD CONSTRAINT fk_payments_perk_selection
            FOREIGN KEY (perk_selection_id) REFERENCES perk_selections(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- FK: payments.provider_id → provider_profiles
-- ON DELETE RESTRICT — payout records must reference a live provider profile.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_payments_provider'
    ) THEN
        ALTER TABLE payments
            ADD CONSTRAINT fk_payments_provider
            FOREIGN KEY (provider_id) REFERENCES provider_profiles(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- FK: payments.employer_id → employer_organizations
-- ON DELETE RESTRICT — spend records must reference the funding employer org.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_payments_employer'
    ) THEN
        ALTER TABLE payments
            ADD CONSTRAINT fk_payments_employer
            FOREIGN KEY (employer_id) REFERENCES employer_organizations(id) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_selection ON payments(perk_selection_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider_id);
CREATE INDEX IF NOT EXISTS idx_payments_employer ON payments(employer_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at);

-- ============================================================
-- Recommender column indexes (001 may already define these; IF NOT EXISTS is safe)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_employee_mode ON employee_profiles(recommender_mode);
CREATE INDEX IF NOT EXISTS idx_employee_onboarding ON employee_profiles(onboarding_completed);
CREATE INDEX IF NOT EXISTS idx_interactions_employee ON perk_interactions(employee_id);
CREATE INDEX IF NOT EXISTS idx_interactions_perk ON perk_interactions(perk_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON perk_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_time ON perk_interactions(occurred_at);

COMMENT ON TABLE perk_interactions IS
    'Append-only recommender training log. Rows are never updated or deleted in application code.';

-- ============================================================
-- Upgrade legacy 002 constraints (from an earlier 002_adr007.sql draft) to named explicit FKs
-- ============================================================

-- Drop unnamed legacy FKs superseded by explicit ON DELETE constraints below.
ALTER TABLE package_items DROP CONSTRAINT IF EXISTS package_items_package_id_fkey;
ALTER TABLE package_items DROP CONSTRAINT IF EXISTS package_items_perk_id_fkey;
ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_perk_selection_id_fkey;
ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_provider_id_fkey;
ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_employer_id_fkey;
ALTER TABLE perk_selections DROP CONSTRAINT IF EXISTS perk_selections_package_id_fkey;

-- Drop unnamed legacy FKs on packages.created_by_user_id if present without SET NULL
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'packages'
          AND c.contype = 'f'
          AND c.conname <> 'fk_packages_created_by_user'
          AND EXISTS (
              SELECT 1 FROM pg_attribute a
              WHERE a.attrelid = t.oid AND a.attname = 'created_by_user_id'
                AND a.attnum = ANY (c.conkey)
          )
    LOOP
        EXECUTE format('ALTER TABLE packages DROP CONSTRAINT %I', r.conname);
    END LOOP;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_packages_created_by_user') THEN
        ALTER TABLE packages
            ADD CONSTRAINT fk_packages_created_by_user
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;
