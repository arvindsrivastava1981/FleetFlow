-- =============================================================================
-- VahanKhata Seed Script: Single Clean Trip Lifecycle (Trip 4191-1)
-- -----------------------------------------------------------------------------
-- Self-contained seed for database/schema.sql. Creates one Fleet, one Vehicle
-- (TS07GK4191), one Trip Manager, one Driver, one Trip (code "4191-1"), and the
-- full set of expenses all chained to that trip.
--
-- DESIGN (per requirement):
--   * INSERT-only — no UPDATE statements anywhere.
--   * Fully sequential — every INSERT is given the id returned by the previous
--     insert via psql \gset, so FKs are exact and never re-queried or patched.
--   * Trip code is the flat "4191-1" (no plate prefix).
--   * Includes every expense type: FUEL, DEF, TOLL, REPAIR, CHALLAN, MISC,
--     GOODS_BUY, GOODS_SALE, plus one flagged FUEL anomaly.
--
-- Roles satisfy the schema CHECK constraints:
--   users.role        IN ('super_admin','trip_manager','driver')
--   trips.status      IN ('ACTIVE','COMPLETED','SETTLED','CANCELLED')
--   expenses.exp_type IN ('FUEL','DEF','TOLL','REPAIR','CHALLAN','MISC',
--                         'GOODS_BUY','GOODS_SALE')
--   manager_status    IN ('PENDING','APPROVED','REJECTED')
--   batta_type        IN ('FIXED_TRIP','PER_KM','DAILY','NONE')
--
-- Run with:  psql "postgres://..." -f database/seed_test_trip.sql
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Fleet
-- ---------------------------------------------------------------------------
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava (Test Fleet)', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

SELECT id AS fleet_id FROM fleets WHERE phone = '+91 98765 00000' \gset

-- ---------------------------------------------------------------------------
-- 2. Trip Manager
-- ---------------------------------------------------------------------------
INSERT INTO users (
    username, password_hash, full_name, role, phone, email,
    fleet_id, is_active, created_by
)
VALUES (
    'test_manager',
    'pbkdf2_sha256$100000$159a80d5e5f6e3cbd4a7022e0ff3c94a$4f02ca54bdb8491179c8ed98b70089a3365d4919d98ca9ad893a522fcb583c0b',
    'Arvind Srivastava (Manager)', 'trip_manager', '+919876500001',
    'test.manager@vahankhata.in',
    :fleet_id, TRUE, NULL
)
ON CONFLICT (username) DO NOTHING;

SELECT id AS manager_id FROM users WHERE username = 'test_manager' \gset
-- ---------------------------------------------------------------------------
-- 3. Driver (flat ₹2,500 batta)
-- ---------------------------------------------------------------------------
INSERT INTO users (
    username, password_hash, full_name, role, phone, email,
    fleet_id, batta_type, default_batta_rate, is_active, created_by
)
VALUES (
    'test_driver',
    'pbkdf2_sha256$100000$93996def8186b585ea6f1f340e97767c$b0ae45aad250ee8e07502f4a8ddf59bd62395e809039522d7f209fd3c40e195d',
    'Ramesh Kumar (Driver)', 'driver', '+919876500002',
    'test.driver@vahankhata.in',
    :fleet_id, 'FIXED_TRIP', 2500.00, TRUE, :manager_id
)
ON CONFLICT (username) DO NOTHING;

SELECT id AS driver_id FROM users WHERE username = 'test_driver' \gset

-- ---------------------------------------------------------------------------
-- 4. Vehicle (TS07GK4191) — owned by the manager
-- ---------------------------------------------------------------------------
INSERT INTO vehicles (
    fleet_id, vehicle_number, make_model, tank_capacity_liters,
    expected_km_per_liter, created_by, is_active
)
VALUES (
    :fleet_id, 'TS07GK4191', 'Tata Prima 5530.S', 350.00, 4.00,
    :manager_id, TRUE
)
ON CONFLICT (vehicle_number) DO NOTHING;

SELECT id AS vehicle_id FROM vehicles WHERE vehicle_number = 'TS07GK4191' \gset

-- ---------------------------------------------------------------------------
-- 5. Trip 4191-1 (ACTIVE)
--    Advance ₹30,000.00 | Flat Batta ₹2,500.00 | Distance 1,450 km
-- ---------------------------------------------------------------------------
INSERT INTO trips (
    fleet_id, trip_code, vehicle_id, vehicle_no, driver_user_id,
    driver_name, driver_phone, advance_amount, driver_batta_amount,
    start_odo, current_odo, end_odo, status, origin, destination, created_by
)
VALUES (
    :fleet_id, '4191-1', :vehicle_id, 'TS07GK4191', :driver_id,
    'Ramesh Kumar (Driver)', '+919876500002',
    30000.00, 2500.00,
    120000, 121450, 121450,
    'ACTIVE', 'Kanpur, UP', 'Bhiwandi, Mumbai',
    :manager_id
)
ON CONFLICT (trip_code) DO NOTHING;

SELECT id AS trip_id FROM trips WHERE trip_code = '4191-1' \gset

-- ---------------------------------------------------------------------------
-- 6. Expenses for trip 4191-1 (all types + flagged anomaly)
-- ---------------------------------------------------------------------------

-- (a) FUEL: approved diesel refill (220 L @ ₹92/L = ₹20,240)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    odometer, station_name, manager_status, reviewed_by, reviewed_at,
    raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'FUEL', 20240.00, 20240.00, 220.0, 92.00, 120650,
    'HPCL Pump Jhansi', 'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '2 days',
    'HPCL Pump Jhansi - Tank Full',
    CURRENT_TIMESTAMP - INTERVAL '2 days'
);

-- (b) DEF (AdBlue): approved 20 L @ ₹60/L = ₹1,200
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'DEF', 1200.00, 1200.00, 20.0, 60.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours',
    'AdBlue 20L Bucket at Dhaba',
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours'
);
-- (c) TOLL: approved toll / FASTag cash bypass
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'TOLL', 1800.00, 1800.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours',
    'MP-MH Border Toll & State Entry Tax',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours'
);

-- (d) REPAIR: approved emergency tyre puncture / valve repair
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'REPAIR', 600.00, 600.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours',
    'Rear Left Tyre Puncture + Air Pressure Check',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours'
);

-- (e) CHALLAN: approved traffic/documentation clearance challan
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'CHALLAN', 1000.00, 1000.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '18 hours',
    'No-Entry Timing Violation Challan receipt verified',
    CURRENT_TIMESTAMP - INTERVAL '18 hours'
);

-- (f) MISC: approved loading / unloading tips (kanta / palledari)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'MISC', 500.00, 500.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '12 hours',
    'Weighbridge (Kanta Parchi) + Palledari',
    CURRENT_TIMESTAMP - INTERVAL '12 hours'
);

-- (g) GOODS_BUY: approved in-transit goods purchase
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'GOODS_BUY', 8000.00, 8000.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '10 hours',
    'Mandi Return Cargo Loading (Agricultural Produce)',
    CURRENT_TIMESTAMP - INTERVAL '10 hours'
);

-- (h) GOODS_SALE: approved cash inflow from goods sale at destination
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'GOODS_SALE', 14000.00, 14000.00,
    'APPROVED', :manager_id,
    CURRENT_TIMESTAMP - INTERVAL '4 hours',
    'Delivered and Cash Collected at Bhiwandi Wholesale Hub',
    CURRENT_TIMESTAMP - INTERVAL '4 hours'
);

-- (i) FLAGGED ANOMALY: suspicious fuel receipt (left PENDING for review).
--     No manager_status='FLAGGED' exists in schema; anomaly is signalled via
--     is_flagged + flag_reason with approved_amount NULL, so the settlement
--     contract excludes it automatically.
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    is_flagged, flag_reason, manager_status, raw_receipt_text, created_at
)
VALUES (
    :trip_id, '4191-1', 'FUEL', 3500.00, NULL, 30.0, 116.66,
    TRUE,
    'Suspicious rate ₹116.66/L exceeds state benchmark (>15% inflation)',
    'PENDING',
    'Suspicious fuel receipt flagged for manager review',
    CURRENT_TIMESTAMP - INTERVAL '2 hours'
);

COMMIT;