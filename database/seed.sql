
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

INSERT INTO vehicles (fleet_id, vehicle_number, tank_capacity_liters, expected_km_per_liter)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'UP-93-AT-1234', 350.00, 4.00
)
ON CONFLICT (vehicle_number) DO NOTHING;

INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter)
VALUES 
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra', 92.80),
    ('DL', 'Delhi', 89.60),
    ('HR', 'Haryana', 90.10);

-- TRIP-104: settled trip with goods buy and sale flow (approved end-to-end)
INSERT INTO trips (trip_code, vehicle_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, end_odo, status, origin, destination, completed_at, settled_at)
VALUES (
    'TRIP-104',
    (SELECT id FROM vehicles WHERE vehicle_number = 'UP-93-AT-1234'),
    'UP-93-AT-1234', 'Rajesh Patel', '+91 98765 33344', 30000.00, 103550.00, 104120.00, 104120.00,
    'SETTLED', 'Jaipur', 'Agra', CURRENT_TIMESTAMP - INTERVAL '12 hours', CURRENT_TIMESTAMP - INTERVAL '12 hours'
)
ON CONFLICT (trip_code) DO NOTHING;

INSERT INTO expenses (trip_id, trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status)
VALUES 
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-104'), 'TRIP-104', 'FUEL', 5400.00, 60.00, 90.00, 103700.00, 'Shell Fuel Station Jaipur', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-104'), 'TRIP-104', 'GOODS_BUY', 15000.00, 0.00, 0.00, 103650.00, 'Jaipur Marble & Tiles Wholesale', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-104'), 'TRIP-104', 'TOLL', 450.00, 0.00, 0.00, 103900.00, 'Agra Expressway Toll', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-104'), 'TRIP-104', 'GOODS_SALE', 22500.00, 0.00, 0.00, 104120.00, 'Agra Retail Store Delivery', FALSE, NULL, 'APPROVED');

-- TRIP-105: settled trip with goods buy and sale flow (approved end-to-end) - textile materials
INSERT INTO trips (trip_code, vehicle_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, end_odo, status, origin, destination, completed_at, settled_at)
VALUES (
    'TRIP-105',
    (SELECT id FROM vehicles WHERE vehicle_number = 'UP-93-AT-1234'),
    'UP-93-AT-1234', 'Vikram Singh', '+91 98765 44455', 28000.00, 104120.00, 104680.00, 104680.00,
    'SETTLED', 'Agra', 'Lucknow', CURRENT_TIMESTAMP - INTERVAL '6 hours', CURRENT_TIMESTAMP - INTERVAL '6 hours'
)
ON CONFLICT (trip_code) DO NOTHING;

INSERT INTO expenses (trip_id, trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status)
VALUES 
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-105'), 'TRIP-105', 'GOODS_BUY', 18500.00, 0.00, 0.00, 104200.00, 'Agra Textile Mills Warehouse', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-105'), 'TRIP-105', 'FUEL', 5850.00, 65.00, 90.00, 104350.00, 'Indian Oil Pump Agra-Lucknow Highway', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-105'), 'TRIP-105', 'TOLL', 520.00, 0.00, 0.00, 104550.00, 'NH-19 Toll Booth', FALSE, NULL, 'APPROVED'),
         ((SELECT id FROM trips WHERE trip_code = 'TRIP-105'), 'TRIP-105', 'GOODS_SALE', 28750.00, 0.00, 0.00, 104680.00, 'Lucknow Fashion District Retail Center', FALSE, NULL, 'APPROVED');

-- ----------------------------------------------------------------------------
-- Seed users: super_admin / trip_manager / driver
-- Passwords: admin123 / manager123 / driver123
-- ----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, full_name, role, phone, email, is_active, created_by)
VALUES
    ('admin', 'pbkdf2_sha256$100000$e736c77949726881ac49aca9b8d141b0$5824b96852d0a9be488b4d67cb40bf66761cb005a709567861bad3139f805b1d',
     'Super Admin', 'super_admin', '+91 98765 00000', 'admin@fleetflow.com', TRUE, NULL),
    ('manager1', 'pbkdf2_sha256$100000$159a80d5e5f6e3cbd4a7022e0ff3c94a$4f02ca54bdb8491179c8ed98b70089a3365d4919d98ca9ad893a522fcb583c0b',
     'Trip Manager', 'trip_manager', '+91 90000 11111', 'manager@fleetflow.com', TRUE, 1),
    ('driver1', 'pbkdf2_sha256$100000$93996def8186b585ea6f1f340e97767c$b0ae45aad250ee8e07502f4a8ddf59bd62395e809039522d7f209fd3c40e195d',
     'Driver One', 'driver', '+91 90000 22222', 'driver@fleetflow.com', TRUE, 2)
ON CONFLICT (username) DO NOTHING;

