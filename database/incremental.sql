-- Allow RTO-FINE and DEF (Diesel Exhaust Fluid/AdBlue/Urea) as expense types
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_exp_type_check
    CHECK (exp_type IN ('FUEL', 'TOLL', 'REPAIR', 'OTHER', 'CHALLAN', 'MISC', 'RTO-FINE', 'DEF'));

-- Track goods purchased from trip advance and sold during the trip.
CREATE TABLE IF NOT EXISTS trip_goods (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
    trip_code VARCHAR(50) NOT NULL REFERENCES trips(trip_code) ON DELETE CASCADE,
    item_name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1.00 CHECK (quantity > 0),
    purchase_cost NUMERIC(12, 2) NOT NULL CHECK (purchase_cost >= 0),
    sale_revenue NUMERIC(12, 2) NOT NULL CHECK (sale_revenue >= 0),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_trip_goods_trip_code ON trip_goods(trip_code);