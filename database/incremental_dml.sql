
-- Incremental script for databases already created from an older schema.sql and this will have only DML statements to bring the database up to date with the latest seed data.
-- ----------------------------------------------------------------------------
INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit, features)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1, '{"vehicle_limit":1,"driver_limit":5,"whatsapp":true,"reports":true}'),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}'),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1, '{"vehicle_limit":1,"driver_limit":10,"whatsapp":true,"reports":true,"batta_profiles":true}')
ON CONFLICT (code) DO NOTHING;
