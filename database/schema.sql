-- ============================================================================
-- VahanKhata: PostgreSQL Master Database Schema
-- Multi-Tenant Fleet Expense Verification & Real-Time Settlement Engine
-- ============================================================================
--
-- Table creation order matters for Foreign Key resolution. Every FK refers to
-- a table created earlier in this file (no forward references):
--   1. subscription_plans
--   2. fleets           -> subscription_plans(id)
--   3. users            -> fleets(id), self-ref users(id)
--   4. vehicles         -> fleets(id), users(id)
--   5. trips            -> fleets(id), vehicles(id), users(id)
--   6. expenses         -> trips(id), users(id)
--   7. fuel_benchmarks

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. SUBSCRIPTION PLANS — the billable product catalogue
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_plans (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,      -- 'TRIAL', 'MONTHLY', 'YEARLY'
    name VARCHAR(80) NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,    -- 'TRIAL', 'MONTHLY', 'YEARLY'
    trial_days INT NOT NULL DEFAULT 0,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    vehicle_limit INT NOT NULL DEFAULT 1,  -- vehicles included with this plan
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. FLEETS / OWNERS — owns the subscription entitlement (state, plan, trial
--    window, Razorpay refs, vehicle cap).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fleets (
    id BIGSERIAL PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(150),
    subscription_plan VARCHAR(50) DEFAULT 'STARTER_PACK',
    plan_id BIGINT REFERENCES subscription_plans(id),
    plan_rate NUMERIC(10, 2) DEFAULT 799.00,
    subscription_status VARCHAR(20) DEFAULT 'TRIAL'
        CHECK (subscription_status IN ('TRIAL','ACTIVE','PAST_DUE','CANCELLED','EXPIRED')),
    trial_started_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    vehicle_limit INT NOT NULL DEFAULT 1,
    next_billing_date DATE,
    razorpay_subscription_id VARCHAR(64),
    razorpay_customer_id VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fleets_phone ON fleets(phone);
-- ----------------------------------------------------------------------------
-- 3. USERS — role-based access (Super Admin / Trip Manager / Driver).
--    Created before vehicles & trips because they reference users(id).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('super_admin', 'trip_manager', 'driver')),
    phone VARCHAR(20),
    email VARCHAR(150),
    fleet_id BIGINT REFERENCES fleets(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    batta_type VARCHAR(20) DEFAULT NULL,
    default_batta_rate NUMERIC(10, 2) DEFAULT NULL
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_fleet_id ON users(fleet_id);

-- ----------------------------------------------------------------------------
-- 4. VEHICLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
    id BIGSERIAL PRIMARY KEY,
    fleet_id BIGINT NOT NULL REFERENCES fleets(id) ON DELETE CASCADE,
    vehicle_number VARCHAR(20) UNIQUE NOT NULL,
    make_model VARCHAR(100),
    tank_capacity_liters NUMERIC(8, 2) NOT NULL DEFAULT 350.00,
    expected_km_per_liter NUMERIC(5, 2) NOT NULL DEFAULT 4.00,
    owner_phone VARCHAR(20),
    created_by BIGINT REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vehicles_number ON vehicles(vehicle_number);
CREATE INDEX IF NOT EXISTS idx_vehicles_fleet_id ON vehicles(fleet_id);

-- ----------------------------------------------------------------------------
-- 5. TRIPS
--    fleet_id is NOT NULL so trip-level data is always tied to an owning fleet
--    (multi-tenant isolation / clean cascade on fleet deletion).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trips (
    id BIGSERIAL PRIMARY KEY,
    fleet_id BIGINT NOT NULL REFERENCES fleets(id) ON DELETE CASCADE,
    trip_code VARCHAR(50) UNIQUE NOT NULL,
    vehicle_id BIGINT REFERENCES vehicles(id) ON DELETE SET NULL,
    vehicle_no VARCHAR(20) NOT NULL,
    driver_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    driver_name VARCHAR(100) NOT NULL,
    driver_phone VARCHAR(20) NOT NULL,
    advance_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    start_odo NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    current_odo NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    end_odo NUMERIC(10, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'COMPLETED', 'SETTLED', 'CANCELLED')),
    origin VARCHAR(100),
    destination VARCHAR(100),
    driver_batta_amount NUMERIC(10, 2) DEFAULT 2500.00,
    verification_hash VARCHAR(32),
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trips_fleet_id ON trips(fleet_id);
CREATE INDEX IF NOT EXISTS idx_trips_trip_code ON trips(trip_code);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
-- ----------------------------------------------------------------------------
-- 6. EXPENSES
--    trip_id is the SOLE foreign key (ON DELETE CASCADE). trip_code is retained
--    purely as an indexed lookup column (NOT NULL) with no FK against
--    trips(trip_code) — the trip identity is owned by trip_id.
--    reviewed_by / reviewed_at capture the manager audit trail.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    trip_code VARCHAR(50) NOT NULL,
    exp_type VARCHAR(20) NOT NULL
        CHECK (exp_type IN ('FUEL', 'DEF', 'TOLL', 'REPAIR', 'CHALLAN', 'MISC', 'GOODS_BUY', 'GOODS_SALE')),
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    approved_amount NUMERIC(10, 2),
    liters NUMERIC(8, 2) DEFAULT 0.00,
    rate NUMERIC(8, 2) DEFAULT 0.00,
    odometer NUMERIC(10, 2) DEFAULT 0.00,
    station_name VARCHAR(255),
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    flag_reason TEXT,
    manager_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (manager_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    reviewed_by BIGINT REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    receipt_image_url TEXT,
    raw_receipt_text TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_trip_id ON expenses(trip_id);
CREATE INDEX IF NOT EXISTS idx_expenses_trip_code ON expenses(trip_code);
CREATE INDEX IF NOT EXISTS idx_expenses_exp_type ON expenses(exp_type);
CREATE INDEX IF NOT EXISTS idx_expenses_is_flagged ON expenses(is_flagged);

-- ----------------------------------------------------------------------------
-- 7. FUEL BENCHMARKS — per-state diesel price index for the anomaly rules engine
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fuel_benchmarks (
    id SERIAL PRIMARY KEY,
    state_code VARCHAR(10) NOT NULL,
    state_name VARCHAR(50) NOT NULL,
    benchmark_price_per_liter NUMERIC(6, 2) NOT NULL,
    tolerance_pct NUMERIC(5, 2) DEFAULT 8.00, -- percentage points (e.g. 8.00%)
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 8. WEBHOOK LOGS — Razorpay webhook deduplication ledger.
--    `event_id` is the Razorpay event id, UNIQUE so a retried delivery of the
--    same `payment_link.paid` (or any future event) cannot apply its side
--    effect (activate plan / bump limit) more than once. The webhook route
--    writes a row here *inside the same transaction* that applies the effect;
--    a second delivery hits the unique constraint / a pre-check and is a no-op.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS webhook_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,     -- Razorpay event.id (stable across retries)
    event_type VARCHAR(64) NOT NULL,          -- e.g. payment_link.paid / subscription.activated
    payload JSONB NOT NULL,                   -- raw event body for audit/replay
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSED'
        CHECK (status IN ('PROCESSED', 'SKIPPED', 'FAILED')),
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_event_id ON webhook_logs(event_id);

-- ----------------------------------------------------------------------------
-- 9. ERROR LOGS — central sink for every error raised on the backend side.
--    `backend/app/core/errors.py` registers global FastAPI exception handlers;
--    whenever an endpoint raises (ApiError, request validation failure, HTTP
--    error, or any uncaught 5xx exception) a row is inserted here for audit,
--    tracing and post-mortem analysis. `traceback_text` holds the full stack
--    for internal (5xx) failures; `detail` stores a JSON-encoded payload for
--    validation/API errors. `source` defaults to 'BACKEND' and can be extended
--    for payment/webhook/whatsapp sub-systems.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS error_logs (
    id BIGSERIAL PRIMARY KEY,
    method VARCHAR(10),                        -- HTTP verb (GET/POST/PUT/PATCH/DELETE)
    path TEXT,                                 -- the request URL path
    status_code INT NOT NULL,                  -- intended HTTP status (400/404/422/500...)
    error_type VARCHAR(30) NOT NULL,           -- API_ERROR | VALIDATION | HTTP | INTERNAL
    message TEXT NOT NULL,                     -- human-readable error message
    detail TEXT,                               -- JSON-encoded payload (validation errors, details)
    traceback_text TEXT,                       -- full stack trace for INTERNAL errors
    endpoint VARCHAR(255),                     -- route/path identifier used for grouping
    source VARCHAR(20) DEFAULT 'BACKEND'
        CHECK (source IN ('BACKEND', 'PAYMENT', 'WHATSAPP', 'WEBHOOK')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_status_code ON error_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);

-- ----------------------------------------------------------------------------
-- AUTOMATED UPDATED_AT TIMESTAMP TRIGGER
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_subscription_plans_updated_at
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_fleets_updated_at
    BEFORE UPDATE ON fleets
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_trips_updated_at
    BEFORE UPDATE ON trips
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_expenses_updated_at
    BEFORE UPDATE ON expenses
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_fuel_benchmarks_updated_at
    BEFORE UPDATE ON fuel_benchmarks
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();