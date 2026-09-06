-- Drop username from auth_sessions
ALTER TABLE auth_sessions DROP COLUMN IF EXISTS username;
-- Make email the unique login key
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE users DROP COLUMN IF EXISTS username;
ALTER TABLE users ALTER COLUMN email SET NOT NULL;
DO $$ BEGIN
    ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;
-- Add email verification columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_token VARCHAR(255) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_expires_at TIMESTAMPTZ DEFAULT NULL;
-- Add social login columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'local';
ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_sub VARCHAR(255) DEFAULT NULL;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_provider_check;
ALTER TABLE users ADD CONSTRAINT users_auth_provider_check CHECK (auth_provider IN ('local', 'google', 'facebook'));
-- Social accounts (google/facebook) are untrusted self-signup: super_admin only
-- ever comes from the manual seed script (database/super_admin.sql), so a
-- non-local provider can never hold the super_admin role.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_should_trip_manger;
ALTER TABLE users ADD CONSTRAINT users_should_trip_manger CHECK (auth_provider = 'local' OR role <> 'super_admin');
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_sub ON users(provider_sub) WHERE provider_sub IS NOT NULL;
-- Email index
DROP INDEX IF EXISTS idx_users_username;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(lower(email));-- 2026-09 Phase 1 (manager data-entry): attribute who entered each expense.
-- DRIVER_WHATSAPP = driver-sent (bot/app) | MANAGER_MANUAL = manager keyed it in
-- on the driver's behalf | AUTO_POST = system-generated (CASH_ADVANCE, DRIVER_SALARY).
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS entry_source VARCHAR(20) NOT NULL DEFAULT 'DRIVER_WHATSAPP';
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_entry_source_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_entry_source_check CHECK (entry_source IN ('DRIVER_WHATSAPP', 'MANAGER_MANUAL', 'AUTO_POST'));
