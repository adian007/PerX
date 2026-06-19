-- PostgreSQL row-level security backstop (minimal hackathon scope).
-- Full multi-tenant RLS across all tables is deferred; perk_selections org isolation
-- is enforced here as a database backstop alongside service-layer RBAC.

-- Enable RLS on perk_selections (policies apply when session sets app.current_org_id).
ALTER TABLE perk_selections ENABLE ROW LEVEL SECURITY;

-- Drop if re-applying during local dev resets.
DROP POLICY IF EXISTS perk_selections_employer_isolation ON perk_selections;

-- Employers see only selections for their organization when current_org_id is set.
CREATE POLICY perk_selections_employer_isolation ON perk_selections
    FOR SELECT
    USING (
        current_setting('app.current_org_id', true) IS NULL
        OR current_setting('app.current_org_id', true) = ''
        OR employer_id::text = current_setting('app.current_org_id', true)
    );

COMMENT ON POLICY perk_selections_employer_isolation ON perk_selections IS
    'Backstop org isolation when app.current_org_id is set by the application session. '
    'Service-layer RBAC remains the primary enforcement path; full RLS on all tenant '
    'tables is intentionally deferred post-hackathon.';
