-- =============================================================================
-- VahanKhata Seed Script: Single Clean Trip Lifecycle (Trip 4191-1)
-- -----------------------------------------------------------------------------
-- Self-contained seed for database/schema.sql. Creates one Fleet, one Vehicle
-- (TS07GK4191), one Trip Manager, one Driver, one Trip (code "4191-1"), and the
-- full set of expenses, all chained to that trip.
--
-- DESIGN (per requirement):
--   * INSERT-only — no UPDATE statements anywhere.
--   * 100% portable plain SQL — runs in any client (psql, DBeaver, DataGrip,
--     TablePlus, Neon). No psql meta-commands (\gset), no DO $$ blocks, and no
--     :named-vars. Every INSERT is one complete statement ending in a single ';'.
--   * Fully sequential — each parent id is resolved with an inline
--     (SELECT id FROM ...) subquery against the row created by the previous
--     INSERT, so the ids always refer to the just-created rows.
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
-- NOTE: When run from a GUI client, execute the WHOLE script once (select all
-- and run) so the id subqueries resolve against rows created earlier in the
-- same run.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Fleet
-- ---------------------------------------------------------------------------
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava (Test Fleet)', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Trip Manager
-- ---------------------------------------------------------------------------
INSERT INTO users (
    username, password_hash, full_name, role, phone, email,
    fleet_id, is_active, created_by
)
SELECT
    'test_manager',
    'pbkdf2_sha256$100000$159a80d5e5f6e3cbd4a7022e0ff3c94a$4f02ca54bdb8491179c8ed98b70089a3365d4919d98ca9ad893a522fcb583c0b',
    'Arvind Srivastava (Manager)', 'trip_manager', '+919876500001',
    'test.manager@vahankhata.in',
    f.id, TRUE, NULL
FROM fleets f
WHERE f.phone = '+91 98765 00000'
ON CONFLICT (username) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Driver (flat ₹2,500 batta)
-- ---------------------------------------------------------------------------
INSERT INTO users (
    username, password_hash, full_name, role, phone, email,
    fleet_id, batta_type, default_batta_rate, is_active, created_by
)
SELECT
    'test_driver',
    'pbkdf2_sha256$100000$93996def8186b585ea6f1f340e97767c$b0ae45aad250ee8e07502f4a8ddf59bd62395e809039522d7f209fd3c40e195d',
    'Ramesh Kumar (Driver)', 'driver', '+919876500002',
    'test.driver@vahankhata.in',
    f.id, 'FIXED_TRIP', 2500.00, TRUE, m.id
FROM fleets f
JOIN users m ON m.username = 'test_manager'
WHERE f.phone = '+91 98765 00000'
ON CONFLICT (username) DO NOTHING;
-- ---------------------------------------------------------------------------
-- 4. Vehicle (TS07GK4191) — owned by the manager
-- ---------------------------------------------------------------------------
INSERT INTO vehicles (
    fleet_id, vehicle_number, make_model, tank_capacity_liters,
    expected_km_per_liter, created_by, is_active
)
SELECT
    f.id, 'TS07GK4191', 'Tata Prima 5530.S', 350.00, 4.00,
    m.id, TRUE
FROM fleets f
JOIN users m ON m.username = 'test_manager'
WHERE f.phone = '+91 98765 00000'
ON CONFLICT (vehicle_number) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Trip 4191-1 (ACTIVE)
--    Advance ₹30,000.00 | Flat Batta ₹2,500.00 | Distance 1,450 km
-- ---------------------------------------------------------------------------
INSERT INTO trips (
    fleet_id, trip_code, vehicle_id, vehicle_no, driver_user_id,
    driver_name, driver_phone, advance_amount, driver_batta_amount,
    start_odo, current_odo, end_odo, status, origin, destination, created_by
)
SELECT
    f.id, '4191-1', v.id, v.vehicle_number, d.id,
    'Ramesh Kumar (Driver)', '+919876500002',
    30000.00, 2500.00,
    120000, 121450, 121450,
    'ACTIVE', 'Kanpur, UP', 'Bhiwandi, Mumbai',
    m.id
FROM fleets f
JOIN vehicles v ON v.vehicle_number = 'TS07GK4191'
JOIN users d ON d.username = 'test_driver'
JOIN users m ON m.username = 'test_manager'
WHERE f.phone = '+91 98765 00000'
ON CONFLICT (trip_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. Expenses for trip 4191-1 (all types + flagged anomaly)
-- ---------------------------------------------------------------------------
-- Each expense is tied to the trip row created above via its unique id, and to
-- the manager id for the audit trail (reviewed_by / created_by equivalent).

-- (a) FUEL: approved diesel refill (220 L @ ₹92/L = ₹20,240)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    odometer, station_name, manager_status, reviewed_by, reviewed_at,
    raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'FUEL', 20240.00, 20240.00, 220.0, 92.00, 120650,
    'HPCL Pump Jhansi', 'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '2 days',
    'HPCL Pump Jhansi - Tank Full',
    CURRENT_TIMESTAMP - INTERVAL '2 days'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (b) DEF (AdBlue): approved 20 L @ ₹60/L = ₹1,200
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'DEF', 1200.00, 1200.00, 20.0, 60.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours',
    'AdBlue 20L Bucket at Dhaba',
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';
-- (c) TOLL: approved toll / FASTag cash bypass
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'TOLL', 1800.00, 1800.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours',
    'MP-MH Border Toll & State Entry Tax',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (d) REPAIR: approved emergency tyre puncture / valve repair
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'REPAIR', 600.00, 600.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours',
    'Rear Left Tyre Puncture + Air Pressure Check',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (e) CHALLAN: approved traffic/documentation clearance challan
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'CHALLAN', 1000.00, 1000.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '18 hours',
    'No-Entry Timing Violation Challan receipt verified',
    CURRENT_TIMESTAMP - INTERVAL '18 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (f) MISC: approved loading / unloading tips (kanta / palledari)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'MISC', 500.00, 500.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '12 hours',
    'Weighbridge (Kanta Parchi) + Palledari',
    CURRENT_TIMESTAMP - INTERVAL '12 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (g) GOODS_BUY: approved in-transit goods purchase
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'GOODS_BUY', 8000.00, 8000.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '10 hours',
    'Mandi Return Cargo Loading (Agricultural Produce)',
    CURRENT_TIMESTAMP - INTERVAL '10 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (h) GOODS_SALE: approved cash inflow from goods sale at destination
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'GOODS_SALE', 14000.00, 14000.00,
    'APPROVED', m.id,
    CURRENT_TIMESTAMP - INTERVAL '4 hours',
    'Delivered and Cash Collected at Bhiwandi Wholesale Hub',
    CURRENT_TIMESTAMP - INTERVAL '4 hours'
FROM trips t
JOIN users m ON m.username = 'test_manager'
WHERE t.trip_code = '4191-1';

-- (i) FLAGGED ANOMALY: suspicious fuel receipt (left PENDING for review).
--     No manager_status='FLAGGED' exists in schema; anomaly is signalled via
--     is_flagged + flag_reason with approved_amount NULL, so the settlement
--     contract excludes it automatically.
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    is_flagged, flag_reason, manager_status, raw_receipt_text, created_at
)
SELECT
    t.id, t.trip_code, 'FUEL', 3500.00, NULL, 30.0, 116.66,
    TRUE,
    'Suspicious rate ₹116.66/L exceeds state benchmark (>15% inflation)',
    'PENDING',
    'Suspicious fuel receipt flagged for manager review',
    CURRENT_TIMESTAMP - INTERVAL '2 hours'
FROM trips t
WHERE t.trip_code = '4191-1';

COMMIT;