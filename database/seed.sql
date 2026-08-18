

-- 15-day free trial for a newly created fleet/trip-manager, then ₹799/mo
-- (or ₹7,191/yr at 25% off). Each plan includes 1 vehicle; extra vehicles
-- are a separate per-vehicle Razorpay purchase.
INSERT INTO fleets (owner_name, phone, plan_rate)
VALUES ('Arvind Srivastava', '+91 98765 00000', 799.00)
ON CONFLICT (phone) DO NOTHING;

INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1)
ON CONFLICT (code) DO NOTHING;

-- Start the seeded fleet in its 15-day trial on the TRIAL plan.
UPDATE fleets SET
    plan_id = (SELECT id FROM subscription_plans WHERE code = 'TRIAL'),
    subscription_status = 'TRIAL',
    trial_started_at = CURRENT_TIMESTAMP,
    trial_ends_at = CURRENT_TIMESTAMP + INTERVAL '15 days',
    vehicle_limit = 1
WHERE phone = '+91 98765 00000';

-- ----------------------------------------------------------------------------
-- admin   admin123
-- manager1   manager123
-- driver1   driver123
-- (Inserted before vehicles because vehicle ownership references these users)
-- ----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, full_name, role, phone, email, is_active, created_by)
VALUES
    ('admin', 'pbkdf2_sha256$100000$e736c77949726881ac49aca9b8d141b0$5824b96852d0a9be488b4d67cb40bf66761cb005a709567861bad3139f805b1d',
     'Super Admin', 'super_admin', '+91 98765 00000', 'admin@vahankhata.in', TRUE, NULL),
    ('manager1', 'pbkdf2_sha256$100000$159a80d5e5f6e3cbd4a7022e0ff3c94a$4f02ca54bdb8491179c8ed98b70089a3365d4919d98ca9ad893a522fcb583c0b',
     'Trip Manager', 'trip_manager', '+91 90000 11111', 'manager@vahankhata.in', TRUE, 1),
    ('driver1', 'pbkdf2_sha256$100000$93996def8186b585ea6f1f340e97767c$b0ae45aad250ee8e07502f4a8ddf59bd62395e809039522d7f209fd3c40e195d',
     'Driver One', 'driver', '+91 90000 22222', 'driver@vahankhata.in', TRUE, 2)
ON CONFLICT (username) DO NOTHING;

INSERT INTO vehicles (fleet_id, vehicle_number, tank_capacity_liters, expected_km_per_liter, created_by)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'UP93AT1234', 350.00, 4.00,
    (SELECT id FROM users WHERE username = 'manager1')
)
ON CONFLICT (vehicle_number) DO NOTHING;

INSERT INTO vehicles (fleet_id, vehicle_number, make_model, tank_capacity_liters, expected_km_per_liter, created_by)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'HR55BG6789', 'Tata 1613', 350.00, 4.00,
    (SELECT id FROM users WHERE username = 'manager1')
)
ON CONFLICT (vehicle_number) DO NOTHING;

INSERT INTO vehicles (fleet_id, vehicle_number, make_model, tank_capacity_liters, expected_km_per_liter, created_by)
VALUES (
    (SELECT id FROM fleets WHERE phone = '+91 98765 00000'),
    'DL10CV1122', 'Ashok Leyland 3118', 350.00, 4.00,
    (SELECT id FROM users WHERE username = 'manager1')
)
ON CONFLICT (vehicle_number) DO NOTHING;

INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter)
VALUES 
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra', 92.80),
    ('DL', 'Delhi', 89.60),
    ('HR', 'Haryana', 90.10);
