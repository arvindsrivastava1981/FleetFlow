-- ============================================================================
-- VahanKhata: Database Cleanup / Reset
--   Drops every table (FK-safe, dependency order) then truncates remaining data.
--   Meant for local dev reset before re-applying schema.sql + seed/incremental.
--   The app never runs this file (zero DDL in-app invariant).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DROP TABLES (dependency order — children before parents)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS webhook_logs CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS fuel_benchmarks CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS fleets CASCADE;
DROP TABLE IF EXISTS subscription_plans CASCADE;
--DROP TABLE IF EXISTS error_logs CASCADE;
DROP TABLE IF EXISTS fleet_billing_events CASCADE;

-- ----------------------------------------------------------------------------
-- DEMO DATA CLEANUP (for schemas kept intact — only sinks seeding re-run)
-- ----------------------------------------------------------------------------
TRUNCATE TABLE webhook_logs CASCADE;
TRUNCATE TABLE expenses CASCADE;
TRUNCATE TABLE trips CASCADE;
TRUNCATE TABLE vehicles CASCADE;
TRUNCATE TABLE fuel_benchmarks CASCADE;
TRUNCATE TABLE users CASCADE;
TRUNCATE TABLE fleets CASCADE;
TRUNCATE TABLE subscription_plans CASCADE;
TRUNCATE TABLE error_logs CASCADE;
TRUNCATE TABLE fleet_billing_events CASCADE;