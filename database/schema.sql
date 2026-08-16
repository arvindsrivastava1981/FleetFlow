-- ============================================================================
-- FleetFlow: PostgreSQL Master Database Schema
-- Multi-Tenant Fleet Expense Verification & Real-Time Settlement Engine
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. FLEETS / OWNERS TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fleets (
    id BIGSERIAL PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(150),
    subscription_plan VARCHAR(50) DEFAULT 'STARTER_PACK',
    plan_rate NUMERIC(10, 2) DEFAULT 799.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fleets_phone ON fleets(phone);

-- ----------------------------------------------------------------------------
-- 2. VEHICLES TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
    id BIGSERIAL PRIMARY KEY,
    fleet_id BIGINT REFERENCES fleets(id) ON DELETE CASCADE,
    vehicle_number VARCHAR(20) UNIQUE NOT NULL,
    make_model VARCHAR(100),
    tank_capacity_liters NUMERIC(8, 2) NOT NULL DEFAULT 350.00,
    expected_km_per_liter NUMERIC(5, 2) NOT NULL DEFAULT 4.00,
    owner_phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vehicles_number ON vehicles(vehicle_number);
CREATE INDEX IF NOT EXISTS idx_vehicles_fleet_id ON vehicles(fleet_id);

-- ----------------------------------------------------------------------------
-- 3. TRIPS TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trips (
    id BIGSERIAL PRIMARY KEY,
    trip_code VARCHAR(50) UNIQUE NOT NULL,
    vehicle_id BIGINT REFERENCES vehicles(id) ON DELETE SET NULL,
    vehicle_no VARCHAR(20) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trips_trip_code ON trips(trip_code);
CREATE INDEX IF NOT EXISTS idx_trips_vehicle_no ON trips(vehicle_no);
CREATE INDEX IF NOT EXISTS idx_trips_driver_phone ON trips(driver_phone);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);

-- ----------------------------------------------------------------------------
-- 4. EXPENSES TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    trip_code VARCHAR(50) NOT NULL REFERENCES trips(trip_code) ON DELETE CASCADE,
    exp_type VARCHAR(20) NOT NULL 
        CHECK (exp_type IN ('FUEL', 'TOLL', 'REPAIR', 'OTHER', 'CHALLAN', 'MISC')),
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
    receipt_image_url TEXT,
    raw_receipt_text TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_trip_code ON expenses(trip_code);
CREATE INDEX IF NOT EXISTS idx_expenses_trip_id ON expenses(trip_id);
CREATE INDEX IF NOT EXISTS idx_expenses_exp_type ON expenses(exp_type);
CREATE INDEX IF NOT EXISTS idx_expenses_is_flagged ON expenses(is_flagged);
CREATE INDEX IF NOT EXISTS idx_expenses_manager_status ON expenses(manager_status);

-- ----------------------------------------------------------------------------
-- 5. FUEL BENCHMARKS TABLE (Reference for anomaly rules engine)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fuel_benchmarks (
    id SERIAL PRIMARY KEY,
    state_code VARCHAR(10) NOT NULL,
    state_name VARCHAR(50) NOT NULL,
    benchmark_price_per_liter NUMERIC(6, 2) NOT NULL,
    tolerance_pct NUMERIC(4, 2) DEFAULT 0.08, -- 8% price band tolerance
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. AUTOMATED UPDATED_AT TIMESTAMP TRIGGER
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_fleets_updated_at
    BEFORE UPDATE ON fleets
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp_column();

CREATE TRIGGER trg_vehicles_updated_at
    BEFORE UPDATE ON vehicles
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
