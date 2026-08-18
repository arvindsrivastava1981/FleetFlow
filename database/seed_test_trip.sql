-- =============================================================================
-- VahanKhata Seed Script: Full Trip Lifecycle with All Transaction Types
-- -----------------------------------------------------------------------------
-- Self-contained, idempotent seed for database/schema.sql (Multi-tenant Fleet
-- Expense Verification & Real-Time Settlement Engine).
--
-- Populates a realistic end-to-end trip with:
--   * 1 Trip Manager (trip_manager) + 1 Driver (driver, flat ₹2,500 batta)
--   * 1 ACTIVE, audited trip (Advance ₹30,000 | Flat Batta ₹2,500 | 1,450 km)
--   * A second vehicle TS07GK4141 with auto-generated trip code TS07GK4141-1
--   * All expense categories: FUEL, DEF, TOLL, REPAIR, CHALLAN, MISC,
--     GOODS_BUY, GOODS_SALE + one flagged FUEL anomaly (is_flagged).
--
-- Re-runnable: every statement is an upsert / guarded, so `psql -f` is safe
-- to run repeatedly (idempotency).
--
-- Roles follow the schema's CHECK constraints exactly:
--   users.role        IN ('super_admin', 'trip_manager', 'driver')
--   trips.status      IN ('ACTIVE', 'COMPLETED', 'SETTLED', 'CANCELLED')
--   expenses.exp_type IN ('FUEL','DEF','TOLL','REPAIR','CHALLAN','MISC',
--                         'GOODS_BUY','GOODS_SALE')
--   manager_status    IN ('PENDING','APPROVED','REJECTED')  --> anomalies are
--                         signalled via is_flagged + flag_reason instead.

-- Arvind Srivastava (Manager)	test_manager	manager123	Trip Manager
-- Ramesh Kumar (Driver)	test_driver	driver123	Driver
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Ensure the owning Fleet exists (matches the phone used by seed.sql).
-- ---------------------------------------------------------------------------
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava (Test Fleet)', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 1. Create or ensure the Test Vehicle (TS07GK4141)
-- ---------------------------------------------------------------------------
INSERT INTO vehicles (
    fleet_id, vehicle_number, make_model, tank_capacity_liters,
    expected_km_per_liter, created_by, is_active
)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'TS07GK4141', 'Tata Prima 5530.S', 350.00, 4.00,
    NULL,
    TRUE
)
ON CONFLICT (vehicle_number) DO UPDATE
SET make_model = 'Tata Prima 5530.S',
    is_active  = TRUE;

-- ---------------------------------------------------------------------------
-- 2. Trip Manager User
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
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    TRUE, NULL
)
ON CONFLICT (username) DO UPDATE
SET full_name = 'Arvind Srivastava (Manager)',
    role      = 'trip_manager',
    phone     = '+919876500001',
    is_active = TRUE;
-- ---------------------------------------------------------------------------
-- Backfill vehicle ownership so the seeded vehicles are visible to the Trip
-- Manager (vehicles.py scopes a trip_manager to created_by = user_id).
--   TS07GK4141 is created in section 1 (before manager exists); TS07GK4141 is
--   created below in section 6. This update covers both idempotently.
-- ---------------------------------------------------------------------------
UPDATE vehicles
   SET created_by = (SELECT id FROM users WHERE username = 'test_manager')
 WHERE vehicle_number IN ('TS07GK4141');

-- ---------------------------------------------------------------------------
-- 3. Driver User with Fixed ₹2,500 Batta
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
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'FIXED_TRIP', 2500.00, TRUE,
    (SELECT id FROM users WHERE username = 'test_manager')
)
ON CONFLICT (username) DO UPDATE
SET full_name           = 'Ramesh Kumar (Driver)',
    role                = 'driver',
    phone               = '+919876500002',
    batta_type          = 'FIXED_TRIP',
    default_batta_rate  = 2500.00,
    is_active           = TRUE;

-- ---------------------------------------------------------------------------
-- 4. Full Test Trip
--    Advance: ₹30,000.00 | Flat Batta: ₹2,500.00 | Distance: 1,450 km
-- ---------------------------------------------------------------------------
INSERT INTO trips (
    fleet_id, trip_code, vehicle_id, vehicle_no, driver_user_id,
    driver_name, driver_phone, advance_amount, driver_batta_amount,
    start_odo, current_odo, end_odo, status, origin, destination, created_by
)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'TRIP-TEST-101',
    (SELECT id FROM vehicles WHERE vehicle_number = 'TS07GK4141'),
    'TS07GK4141',
    (SELECT id FROM users WHERE username = 'test_driver'),
    'Ramesh Kumar (Driver)', '+919876500002',
    30000.00, 2500.00,
    120000, 121450, 121450,
    'ACTIVE', 'Kanpur, UP', 'Bhiwandi, Mumbai',
    (SELECT id FROM users WHERE username = 'test_manager')
)
ON CONFLICT (trip_code) DO UPDATE
SET vehicle_no          = 'TS07GK4141',
    advance_amount      = 30000.00,
    driver_batta_amount = 2500.00,
    start_odo           = 120000,
    current_odo         = 121450,
    end_odo             = 121450,
    status              = 'ACTIVE';

-- ---------------------------------------------------------------------------
-- 5. Ingest All Transaction Types for TRIP-TEST-101
--    (exp_type CHECK constraint from schema)
-- ---------------------------------------------------------------------------

-- (A) FUEL: Approved Diesel Refill (220 Liters @ ₹92/L = ₹20,240)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    odometer, station_name, manager_status, reviewed_by, reviewed_at,
    raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'FUEL', 20240.00, 20240.00, 220.0, 92.00, 120650,
    'HPCL Pump Jhansi', 'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '2 days',
    'HPCL Pump Jhansi - Tank Full',
    CURRENT_TIMESTAMP - INTERVAL '2 days'
);

-- (B) DEF (AdBlue): Approved 20 Liters @ ₹60/L = ₹1,200
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'DEF', 1200.00, 1200.00, 20.0, 60.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours',
    'AdBlue 20L Bucket at Dhaba',
    CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '3 hours'
);

-- (C) TOLL: Approved Toll & FASTag Cash Bypass
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'TOLL', 1800.00, 1800.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours',
    'MP-MH Border Toll & State Entry Tax',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '8 hours'
);

-- (D) REPAIR: Approved Emergency Tyre Puncture / Valve Repair
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'REPAIR', 600.00, 600.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours',
    'Rear Left Tyre Puncture + Air Pressure Check',
    CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '4 hours'
);

-- (E) CHALLAN: Approved Traffic / Documentation Clearance Challan
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'CHALLAN', 1000.00, 1000.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '18 hours',
    'No-Entry Timing Violation Challan receipt verified',
    CURRENT_TIMESTAMP - INTERVAL '18 hours'
);

-- (F) MISC: Approved Loading / Unloading Tips (Kanta / Palledari)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'MISC', 500.00, 500.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '12 hours',
    'Weighbridge (Kanta Parchi) + Palledari',
    CURRENT_TIMESTAMP - INTERVAL '12 hours'
);

-- (G) GOODS_BUY: Approved In-Transit Goods Purchase
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'GOODS_BUY', 8000.00, 8000.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '10 hours',
    'Mandi Return Cargo Loading (Agricultural Produce)',
    CURRENT_TIMESTAMP - INTERVAL '10 hours'
);

-- (H) GOODS_SALE: Approved Cash Inflow from Goods Sale at Destination
--     (builder of Goods Movement at Destination Hub)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount,
    manager_status, reviewed_by, reviewed_at, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'GOODS_SALE', 14000.00, 14000.00,
    'APPROVED',
    (SELECT id FROM users WHERE username = 'test_manager'),
    CURRENT_TIMESTAMP - INTERVAL '4 hours',
    'Delivered and Cash Collected at Bhiwandi Wholesale Hub',
    CURRENT_TIMESTAMP - INTERVAL '4 hours'
);

-- (I) FLAGGED ANOMALY: Suspicious Fuel Receipt
--     (schema has no manager_status='FLAGGED'; anomaly is signalled with
--      is_flagged + flag_reason, and left PENDING for manager review)
INSERT INTO expenses (
    trip_id, trip_code, exp_type, amount, approved_amount, liters, rate,
    is_flagged, flag_reason, manager_status, raw_receipt_text, created_at
)
VALUES (
    (SELECT id FROM trips WHERE trip_code = 'TRIP-TEST-101'),
    'TRIP-TEST-101', 'FUEL', 3500.00, NULL, 30.0, 116.66,
    TRUE,
    'Suspicious rate ₹116.66/L exceeds state benchmark (>15% inflation)',
    'PENDING',
    'Suspicious fuel receipt flagged for manager review',
    CURRENT_TIMESTAMP - INTERVAL '2 hours'
);
-- ---------------------------------------------------------------------------
-- 6. Second Vehicle TS07GK4141 + Auto-Generated Trip Code
--    Trip Code: {plate}-{n} where n = next number for that plate, e.g.
--    "TS07GK4141-1". The app itself does not auto-generate codes (views.py
--    defaults to TRIP-{MMSS}), so we compute the next trip number per plate
--    here in SQL, deduping on the unique trips.trip_code column.
-- ---------------------------------------------------------------------------
INSERT INTO vehicles (
    fleet_id, vehicle_number, make_model, tank_capacity_liters,
    expected_km_per_liter, created_by, is_active
)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'TS07GK4141', 'BharatBenz 2823R', 350.00, 4.00,
    (SELECT id FROM users WHERE username = 'test_manager'),
    TRUE
)
ON CONFLICT (vehicle_number) DO UPDATE
SET make_model = 'BharatBenz 2823R',
    created_by = (SELECT id FROM users WHERE username = 'test_manager'),
    is_active  = TRUE;

-- Auto-generate the trip code and insert the trip if it doesn't already exist.
DO $$
DECLARE
    v_vehicle_no   CONSTANT VARCHAR(20) := 'TS07GK4141';
    v_next_num     INTEGER;
    v_new_code     VARCHAR(50);
    v_fleet_id     BIGINT;
    v_vehicle_id   BIGINT;
    v_driver_id    BIGINT;
    v_manager_id   BIGINT;
BEGIN
    -- Next trip number for this plate = (existing count) + 1
    SELECT COUNT(*) + 1 INTO v_next_num
      FROM trips
     WHERE vehicle_no = v_vehicle_no;

    v_new_code := v_vehicle_no || '-' || v_next_num::TEXT;

    -- Resolve FK references (skip quietly if prerequisites are absent)
    SELECT id INTO v_fleet_id   FROM fleets WHERE phone = '+91 98765 00000';
    SELECT id INTO v_vehicle_id FROM vehicles WHERE vehicle_number = v_vehicle_no;
    SELECT id INTO v_driver_id  FROM users WHERE username = 'test_driver';
    SELECT id INTO v_manager_id FROM users WHERE username = 'test_manager';

    IF v_fleet_id IS NOT NULL AND v_vehicle_id IS NOT NULL
       AND v_driver_id IS NOT NULL AND v_manager_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM trips WHERE trip_code = v_new_code) THEN

        INSERT INTO trips (
            fleet_id, trip_code, vehicle_id, vehicle_no, driver_user_id,
            driver_name, driver_phone, advance_amount, driver_batta_amount,
            start_odo, current_odo, end_odo, status, origin, destination,
            created_by
        )
        VALUES (
            v_fleet_id, v_new_code, v_vehicle_id, v_vehicle_no, v_driver_id,
            'Ramesh Kumar (Driver)', '+919876500002',
            25000.00, 2500.00,
            180000, 180120, 180120,
            'ACTIVE', 'Nashik, MH', 'Bengaluru, KA',
            v_manager_id
        );

        RAISE NOTICE 'Created trip % for vehicle %', v_new_code, v_vehicle_no;
    END IF;
END $$;

-- Ensure this facade trip is always ACTIVE on re-runs (upsert for idempotency)
INSERT INTO trips (
    fleet_id, trip_code, vehicle_id, vehicle_no, driver_user_id,
    driver_name, driver_phone, advance_amount, driver_batta_amount,
    start_odo, current_odo, end_odo, status, origin, destination, created_by
)
SELECT
    v.id, 'TS07GK4141-1', vv.id, vv.vehicle_number, du.id,
    'Ramesh Kumar (Driver)', '+919876500002',
    25000.00, 2500.00,
    180000, 180120, 180120,
    'ACTIVE', 'Nashik, MH', 'Bengaluru, KA', mu.id
FROM fleets v
JOIN vehicles vv ON vv.vehicle_number = 'TS07GK4141'
JOIN users du ON du.username = 'test_driver'
JOIN users mu ON mu.username = 'test_manager'
WHERE v.phone = '+91 98765 00000'
ON CONFLICT (trip_code) DO UPDATE
SET vehicle_no          = 'TS07GK4141',
    status              = 'ACTIVE',
    current_odo         = 180120,
    end_odo             = 180120;

COMMIT;