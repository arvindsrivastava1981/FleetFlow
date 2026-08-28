
-- ----------------------------------------------------------------------------
-- SUPER ADMIN — the single privileged bootstrap account.
--   username : admin
--   password : admin123
-- (Hash matches seed.sql; stored standalone, no fleet linkage.)
-- ----------------------------------------------------------------------------
INSERT INTO users (email, password_hash, full_name, role, phone, is_active, created_by)
VALUES (
    'admin@vahankhata.in',
    'pbkdf2_sha256$100000$e736c77949726881ac49aca9b8d141b0$5824b96852d0a9be488b4d67cb40bf66761cb005a709567861bad3139f805b1d',
    'Super Admin',
    'super_admin',
    '+91 98765 00000',
    TRUE,
    NULL
)
ON CONFLICT (email) DO NOTHING;