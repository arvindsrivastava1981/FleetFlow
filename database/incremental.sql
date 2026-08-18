-- Allow RTO-FINE and DEF (Diesel Exhaust Fluid/AdBlue/Urea) as expense types
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_exp_type_check
    CHECK (exp_type IN ('FUEL', 'TOLL', 'REPAIR', 'OTHER', 'CHALLAN', 'MISC', 'RTO-FINE', 'DEF', 'GOODS_BUY', 'GOODS_SALE'));

-- Remove the retired goods trading feature and its data.
DROP TABLE IF EXISTS trip_goods;

-- ----------------------------------------------------------------------------
-- Users table for role-based access control (Super Admin / Trip Manager / Driver)
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
    is_active BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Trip ownership columns (added to existing trips table)
ALTER TABLE trips ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);
ALTER TABLE trips ADD COLUMN IF NOT EXISTS driver_user_id BIGINT REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_trips_created_by ON trips(created_by);
CREATE INDEX IF NOT EXISTS idx_trips_driver_user_id ON trips(driver_user_id);

-- Vehicle ownership: which Trip Manager / Super Admin created each vehicle so
-- managers see the vehicles they registered and can load them in the trip form.
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_vehicles_created_by ON vehicles(created_by);

-- ----------------------------------------------------------------------------
-- Subscription & fleet-management integration (fleet <-> trip manager, billing)
-- ----------------------------------------------------------------------------

-- 1. Subscription plans catalogue (billable product objects).
CREATE TABLE IF NOT EXISTS subscription_plans (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(80) NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,
    trial_days INT NOT NULL DEFAULT 0,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    vehicle_limit INT NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Extend fleets with subscription + trial + Razorpay state.
ALTER TABLE fleets
    ADD COLUMN IF NOT EXISTS plan_id BIGINT REFERENCES subscription_plans(id),
    ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'TRIAL'
        CHECK (subscription_status IN ('TRIAL','ACTIVE','PAST_DUE','CANCELLED','EXPIRED')),
    ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS vehicle_limit INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS next_billing_date DATE,
    ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(64);

-- 3. Link users to their fleet.
ALTER TABLE users ADD COLUMN IF NOT EXISTS fleet_id BIGINT REFERENCES fleets(id);
CREATE INDEX IF NOT EXISTS idx_users_fleet_id ON users(fleet_id);

-- 4. Seed the default plan catalogue (idempotent on code).
INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1)
ON CONFLICT (code) DO NOTHING;

-- 5. Update the seeded fleet with trial state + plan linkage.
UPDATE fleets SET
    plan_id = (SELECT id FROM subscription_plans WHERE code = 'TRIAL'),
    subscription_status = 'TRIAL',
    trial_started_at = CURRENT_TIMESTAMP,
    trial_ends_at = CURRENT_TIMESTAMP + INTERVAL '15 days',
    vehicle_limit = 1
WHERE plan_id IS NULL;