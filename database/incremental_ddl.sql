-- ============================================================================
-- Incremental script for databases already created from an older schema.sql and this will have only ddl Statements to bring the database up to date with the latest schema.sql.
--

-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;








