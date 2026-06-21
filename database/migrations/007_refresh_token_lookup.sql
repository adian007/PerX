-- O(1) refresh token lookup via SHA-256 digest (bcrypt remains for verification)

ALTER TABLE refresh_tokens
    ADD COLUMN IF NOT EXISTS lookup_hash VARCHAR(64);

-- Existing rows cannot be backfilled without plaintext tokens; force re-auth.
UPDATE refresh_tokens SET is_revoked = TRUE WHERE lookup_hash IS NULL;
DELETE FROM refresh_tokens WHERE lookup_hash IS NULL;

ALTER TABLE refresh_tokens
    ALTER COLUMN lookup_hash SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_lookup_hash
    ON refresh_tokens(lookup_hash);
