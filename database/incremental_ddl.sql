-- ============================================================================
-- Incremental script for databases already created from an older schema.sql and this will have only ddl Statements to bring the database up to date with the latest schema.sql.
--

-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- SETTLEMENT_TRANSFER expense type (driver-initiated settlement closing entry).
-- The inline CHECK in older schema.sql builds auto-name `expenses_exp_type_check`;
-- swap it idempotently so legacy databases accept the new ledger row type.
-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_exp_type_check
        CHECK (exp_type IN ('FUEL', 'DEF', 'TOLL', 'REPAIR', 'CHALLAN', 'MISC',
                            'GOODS_BUY', 'GOODS_SALE', 'CASH_ADVANCE',
                            'DRIVER_SALARY', 'SETTLEMENT_TRANSFER'));

-- ----------------------------------------------------------------------------
-- RULES & RATES page (2026-08): per-user favorites, manager usual-state, and
-- previous-price capture driving the ▲/▼ Change column.
-- ----------------------------------------------------------------------------
ALTER TABLE fuel_benchmarks ADD COLUMN IF NOT EXISTS previous_price NUMERIC(6, 2);
ALTER TABLE users ADD COLUMN IF NOT EXISTS home_state_code VARCHAR(10);

CREATE TABLE IF NOT EXISTS benchmark_favorites (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state_code VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, state_code)
);

CREATE INDEX IF NOT EXISTS idx_benchmark_favorites_user ON benchmark_favorites(user_id);

-- ---------------------------------------------------------------------------- 
-- Audit R-1: durable auth sessions + persistent login throttle.
-- Mirrors the in-process dicts in core/security.py; see db/queries/auth_store.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS login_throttle (
    ip VARCHAR(64) PRIMARY KEY,
    failures INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);









