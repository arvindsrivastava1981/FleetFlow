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

-- ----------------------------------------------------------------------------
-- MASTER DATA (1) — Subscription plan catalogue (billable product objects),
-- idempotent on the unique code.
-- ----------------------------------------------------------------------------
INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit, features)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1, '{"vehicle_limit":1,"driver_limit":5,"whatsapp":true,"reports":true}'),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}'),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}')
ON CONFLICT (code) DO UPDATE SET
    features = EXCLUDED.features,
    name = EXCLUDED.name,
    price = EXCLUDED.price,
    vehicle_limit = EXCLUDED.vehicle_limit;

-- ----------------------------------------------------------------------------
-- MASTER DATA (2) — Per-state diesel price index for the anomaly rules engine.
-- fuel_benchmarks has no unique constraint on state_code, so guard the insert
-- against re-running when a row for that state already exists.
-- ----------------------------------------------------------------------------
INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter, tolerance_pct)
SELECT v.state_code, v.state_name, v.benchmark_price_per_liter, 8.00
FROM (VALUES
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra',   92.80),
    ('DL', 'Delhi',         89.60),
    ('HR', 'Haryana',       90.10)
) AS v(state_code, state_name, benchmark_price_per_liter)
WHERE NOT EXISTS (
    SELECT 1 FROM fuel_benchmarks f WHERE f.state_code = v.state_code
);
