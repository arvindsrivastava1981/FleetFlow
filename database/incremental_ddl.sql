-- ============================================================================
-- Incremental script for databases already created from an older schema.sql and this will have only ddl Statements to bring the database up to date with the latest schema.sql.
--

-- ----------------------------------------------------------------------------

-- Social login (Google / Facebook) — identity columns on users.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'local';
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS provider_sub VARCHAR(255) DEFAULT NULL;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_provider_check;
ALTER TABLE users
    ADD CONSTRAINT users_auth_provider_check
        CHECK (auth_provider IN ('local', 'google', 'facebook'));
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_sub
    ON users(provider_sub) WHERE provider_sub IS NOT NULL;

-- Email verification for local accounts (signup).
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verify_token VARCHAR(255) DEFAULT NULL;
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verify_expires_at TIMESTAMPTZ DEFAULT NULL;

