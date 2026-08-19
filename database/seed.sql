
INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit, features)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1, '{"vehicle_limit":1,"driver_limit":5,"whatsapp":true,"reports":true}'),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}'),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}')
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- admin   admin123
-- ----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, full_name, role, phone, email, is_active, created_by)
VALUES
    ('admin', 'pbkdf2_sha256$100000$e736c77949726881ac49aca9b8d141b0$5824b96852d0a9be488b4d67cb40bf66761cb005a709567861bad3139f805b1d',
     'Super Admin', 'super_admin', '+91 98765 00000', 'admin@vahankhata.in', TRUE, NULL)   
ON CONFLICT (username) DO NOTHING;


INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter)
VALUES 
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra', 92.80),
    ('DL', 'Delhi', 89.60),
    ('HR', 'Haryana', 90.10);
