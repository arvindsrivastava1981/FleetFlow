-- ============================================================================
-- Incremental script for databases already created from the new schema.sql.
--
-- database/schema.sql now defines every table natively (users, vehicles, trips,
-- expenses with the new exp_type whitelist, subscription_plans, fleet billing
-- columns, fuel_benchmarks), so this script only loads REFERENCE/MASTER data and
-- the single privileged bootstrap account. There are no structural migrations
-- here.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- MASTER DATA (1) — Subscription plan catalogue (billable product objects),
-- idempotent on the unique code.
-- ----------------------------------------------------------------------------
INSERT INTO subscription_plans (code, name, billing_cycle, trial_days, price, vehicle_limit)
VALUES
    ('TRIAL',   '15-Day Free Trial',   'TRIAL',   15, 0.00,  1),
    ('MONTHLY', 'Monthly ₹799 Plan',   'MONTHLY',  0, 799.00, 1),
    ('YEARLY',  'Yearly ₹7,191 Plan (25% off)', 'YEARLY', 0, 7191.00, 1)
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- MASTER DATA (2) — Per-state diesel price index for the anomaly rules engine.
-- fuel_benchmarks has no unique constraint on state_code, so guard the insert
-- against re-running when a row for that state already exists.
-- ----------------------------------------------------------------------------
INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter, tolerance_pct)
SELECT v.state_code, v.state_name, v.benchmark_price_per_liter, 8.00
FROM (VALUES
    ('UP', 'Uttar Pradesh', 90.50),
    ('MP', 'Madhya Pradesh', 93.20),
    ('MH', 'Maharashtra',   92.80),
    ('DL', 'Delhi',         89.60),
    ('HR', 'Haryana',       90.10)
) AS v(state_code, state_name, benchmark_price_per_liter)
WHERE NOT EXISTS (
    SELECT 1 FROM fuel_benchmarks f WHERE f.state_code = v.state_code
);

-- ----------------------------------------------------------------------------
-- SUPER ADMIN — the single privileged bootstrap account.
--   username : admin
--   password : admin123
-- (Hash matches seed.sql; stored standalone, no fleet linkage.)
-- ----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, full_name, role, phone, email, is_active, created_by)
VALUES (
    'admin',
    'pbkdf2_sha256$100000$e736c77949726881ac49aca9b8d141b0$5824b96852d0a9be488b4d67cb40bf66761cb005a709567861bad3139f805b1d',
    'Super Admin',
    'super_admin',
    '+91 98765 00000',
    'admin@vahankhata.in',
    TRUE,
    NULL
)
ON CONFLICT (username) DO NOTHING;