
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

