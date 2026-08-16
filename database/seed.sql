
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

-- TRIP-101: settled trip, mix of approved and rejected expenses
INSERT INTO trips (trip_code, vehicle_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, end_odo, status, origin, destination, completed_at, settled_at)
VALUES (
    'TRIP-101',
    (SELECT id FROM vehicles WHERE vehicle_number = 'UP-93-AT-1234'),
    'UP-93-AT-1234', 'Ramesh Kumar', '+91 98765 43210', 25000.00, 102400.00, 102850.00, 102850.00,
    'SETTLED', 'Lucknow', 'Kanpur', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days'
)
ON CONFLICT (trip_code) DO NOTHING;

INSERT INTO expenses (trip_id, trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status)
VALUES 
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-101'), 'TRIP-101', 'FUEL', 4500.00, 50.00, 90.00, 102600.00, 'Indian Oil Highway Pump', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-101'), 'TRIP-101', 'TOLL', 850.00, 0.00, 0.00, 102750.00, 'NH-19 Toll Plaza', TRUE, 'Cash claimed on 100% FASTag corridor', 'REJECTED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-101'), 'TRIP-101', 'FUEL', 5400.00, 60.00, 90.00, 102850.00, 'HPCL Fuel Stop', TRUE, 'Low mileage 1.7 km/L (Expected ~4.0 km/L)', 'REJECTED');

-- TRIP-102: second settled trip on the same vehicle, starting where TRIP-101 ended
INSERT INTO trips (trip_code, vehicle_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, end_odo, status, origin, destination, completed_at, settled_at)
VALUES (
    'TRIP-102',
    (SELECT id FROM vehicles WHERE vehicle_number = 'UP-93-AT-1234'),
    'UP-93-AT-1234', 'Suresh Yadav', '+91 98765 11122', 20000.00, 102850.00, 103400.00, 103400.00,
    'SETTLED', 'Kanpur', 'Delhi', CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP - INTERVAL '1 day'
)
ON CONFLICT (trip_code) DO NOTHING;

INSERT INTO expenses (trip_id, trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status)
VALUES 
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-102'), 'TRIP-102', 'FUEL', 4950.00, 55.00, 90.00, 103100.00, 'Bharat Petroleum Pump', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-102'), 'TRIP-102', 'TOLL', 620.00, 0.00, 0.00, 103200.00, 'Yamuna Expressway Toll', FALSE, NULL, 'APPROVED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-102'), 'TRIP-102', 'REPAIR', 1800.00, 0.00, 0.00, 103300.00, 'Roadside Tyre Repair', TRUE, 'Repair cost above typical range for tyre puncture', 'REJECTED'),
    ((SELECT id FROM trips WHERE trip_code = 'TRIP-102'), 'TRIP-102', 'CHALLAN', 500.00, 0.00, 0.00, 103400.00, 'Traffic Police Checkpoint', TRUE, 'No supporting challan receipt uploaded', 'REJECTED');

