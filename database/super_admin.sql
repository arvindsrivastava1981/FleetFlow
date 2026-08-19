
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