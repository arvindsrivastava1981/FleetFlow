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