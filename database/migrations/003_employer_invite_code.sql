-- Add employer invite codes for employee self-registration (security layer Day 1)

ALTER TABLE employer_organizations
    ADD COLUMN IF NOT EXISTS invite_code VARCHAR(32);

UPDATE employer_organizations
SET invite_code = 'PERX-' || UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
WHERE invite_code IS NULL;

ALTER TABLE employer_organizations
    ALTER COLUMN invite_code SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_employer_invite_code ON employer_organizations(invite_code);
