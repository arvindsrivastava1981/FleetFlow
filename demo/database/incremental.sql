
-- ----------------------------------------------------------------------------
-- 7. SEED DATA FOR TESTING & DEMO
-- ----------------------------------------------------------------------------
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

INSERT INTO vehicles (fleet_id, vehicle_number, tank_capacity_liters, expected_km_per_liter)
VALUES (1, 'UP-93-AT-1234', 350.00, 4.00)
ON CONFLICT (vehicle_number) DO NOTHING;

INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter)
VALUES 
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra', 92.80),
    ('DL', 'Delhi', 89.60),
    ('HR', 'Haryana', 90.10);

INSERT INTO trips (trip_code, vehicle_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, status)
VALUES ('TRIP-101', 1, 'UP-93-AT-1234', 'Ramesh Kumar', '+91 98765 43210', 25000.00, 102400.00, 102850.00, 'ACTIVE')
ON CONFLICT (trip_code) DO NOTHING;

INSERT INTO expenses (trip_id, trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status)
VALUES 
    (1, 'TRIP-101', 'FUEL', 4500.00, 50.00, 90.00, 102600.00, 'Indian Oil Highway Pump', FALSE, NULL, 'APPROVED'),
    (1, 'TRIP-101', 'TOLL', 850.00, 0.00, 0.00, 102750.00, 'NH-19 Toll Plaza', TRUE, 'Cash claimed on 100% FASTag corridor', 'PENDING'),
    (1, 'TRIP-101', 'FUEL', 5400.00, 60.00, 90.00, 102850.00, 'HPCL Fuel Stop', TRUE, 'Low mileage 1.7 km/L (Expected ~4.0 km/L)', 'PENDING');