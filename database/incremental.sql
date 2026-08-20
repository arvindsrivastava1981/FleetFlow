-- ============================================================================
-- Incremental script for databases already created from an older schema.sql.
--
-- database/schema.sql defines every table natively (users, vehicles, trips,
-- expenses with the new exp_type whitelist, subscription_plans, fleet billing
-- columns, fuel_benchmarks, webhook_logs). This file is the SINGLE changelog
-- for databases that predate a table: any structural additions that were once
-- shipped as migrations are re-applied here as idempotent DDL at the top, then
-- REFERENCE/MASTER data and the single privileged bootstrap account are loaded.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- ERROR LOGS — central sink for backend-raised errors (see schema.sql for the
-- column semantics). Created by `backend/app/core/errors.py` global handlers.
-- Idempotent: `IF NOT EXISTS` makes re-runs of this script a no-op.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    method VARCHAR(10),
    path TEXT,
    status_code INT NOT NULL,
    error_type VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    detail TEXT,
    traceback_text TEXT,
    endpoint VARCHAR(255),
    source VARCHAR(20) DEFAULT 'BACKEND'
        CHECK (source IN ('BACKEND', 'PAYMENT', 'WHATSAPP', 'WEBHOOK')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_status_code ON error_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);

-- ----------------------------------------------------------------------------
-- EXPENSES — extend the exp_type whitelist with the auto-posted ledger entries
-- (CASH_ADVANCE = credit to driver, DRIVER_SALARY = debit for batta). These are
-- inserted by the backend at trip-creation; they are never submitted through the
-- rules/flag pipeline. Postgres CHECK constraints cannot be `IF NOT EXISTS`, so
-- refresh idempotently by dropping + re-adding under the same name.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
    ALTER TABLE expenses ADD CONSTRAINT expenses_exp_type_check
        CHECK (exp_type IN ('FUEL', 'DEF', 'TOLL', 'REPAIR', 'CHALLAN', 'MISC',
                            'GOODS_BUY', 'GOODS_SALE', 'CASH_ADVANCE', 'DRIVER_SALARY'));
END $$;

-- ----------------------------------------------------------------------------
-- ONBOARDING / ENTITLEMENT UPGRADES (idempotent) — new columns + fleet_billing_events
-- ledger introduced with the "fleet = transport firm" model. All statements are
-- `IF NOT EXISTS` so re-runs against an already-upgraded DB are a no-op.
-- ----------------------------------------------------------------------------
-- Plan capability matrix: replace the single vehicle_limit with an extensible
-- JSONB feature set (vehicle_limit / driver_limit / whatsapp / reports / ...).
ALTER TABLE subscription_plans
    ADD COLUMN IF NOT EXISTS features JSONB NOT NULL DEFAULT '{}';

-- Fleet entitlement add-ons (extra bought capacity) + default-fleet anchor for
-- reliable tenant routing (G5/G7). Keeps plan baseline separate from add-ons.
ALTER TABLE fleets
    ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS entitlement_addons JSONB NOT NULL DEFAULT '{}';

-- Firm position inside a fleet (owner / manager / branch_head / driver) —
-- extends the platform role without breaking the existing role CHECK.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS fleet_role VARCHAR(20) DEFAULT NULL
        CHECK (fleet_role IN ('owner', 'manager', 'branch_head', 'driver')),
    ADD COLUMN IF NOT EXISTS onboarding_email_at TIMESTAMPTZ;

-- Settlement consent trail on trips (Option 1): manager consents implicitly at
-- settle time, the driver consents explicitly via WhatsApp. Timestamps are DB-
-- authoritative and the actor ids come from the authenticated identity, so the
-- bilingual PDF consent block is auditable. Idempotent for pre-existing DBs.
ALTER TABLE trips
    ADD COLUMN IF NOT EXISTS manager_consent_by BIGINT REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS manager_consent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS driver_consent_by BIGINT REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS driver_consent_at TIMESTAMPTZ;

-- Append-only billing audit ledger: plan changes, extra slots, trial starts.
CREATE TABLE IF NOT EXISTS fleet_billing_events (
    id BIGSERIAL PRIMARY KEY,
    fleet_id BIGINT NOT NULL REFERENCES fleets(id) ON DELETE CASCADE,
    event_type VARCHAR(30) NOT NULL
        CHECK (event_type IN ('PLAN_CHANGE', 'EXTRA_SLOT', 'TRIAL_START', 'PAYMENT')),
    plan_code VARCHAR(30),
    payload JSONB NOT NULL DEFAULT '{}',
    razorpay_ref VARCHAR(64),
    amount NUMERIC(10, 2),
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fleet_events_fleet_id ON fleet_billing_events(fleet_id);
CREATE INDEX IF NOT EXISTS idx_fleet_events_created_at ON fleet_billing_events(created_at DESC);

-- Drop the orphan updated_at trigger on `trips`. Older schema.sql (pre-settlement)
-- created trg_trips_updated_at, but `trips` has NO updated_at column, so any
-- `UPDATE trips` (e.g. /settle) raised: record "new" has no field "updated_at".
DROP TRIGGER IF EXISTS trg_trips_updated_at ON trips;
-- Drop denormalized driver columns from trips (2026-08). driver_name and
-- driver_phone are now derived from the users table via driver_user_id JOIN
-- at query time. The columns are safe to drop: driver_user_id FK already
-- existed and all reader queries have been updated.
ALTER TABLE trips DROP COLUMN IF EXISTS driver_name;
ALTER TABLE trips DROP COLUMN IF EXISTS driver_phone;

