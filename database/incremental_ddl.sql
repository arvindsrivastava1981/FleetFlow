-- ============================================================================
-- Incremental script for databases already created from an older schema.sql and this will have only ddl Statements to bring the database up to date with the latest schema.sql.
--

-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;


-- ----------------------------------------------------------------------------
-- Fuel live-rates upsert needs a UNIQUE key on state_code (benchmarks sync).
-- ----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_fuel_benchmarks_state_code
    ON fuel_benchmarks (state_code);

-- ----------------------------------------------------------------------------
-- Trips: capture the operating state (derived from origin) so the rules engine
-- can pick a per-state fuel benchmark band instead of the global default.
-- ----------------------------------------------------------------------------
ALTER TABLE trips ADD COLUMN IF NOT EXISTS state_code VARCHAR(10);

-- ----------------------------------------------------------------------------
-- Expenses: store the fueling state the driver picks per fuel purchase, so the
-- rules engine evaluates the fuel band against the state where the fuel was
-- actually bought (not the vehicle's registration state).
-- ----------------------------------------------------------------------------
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS state_code VARCHAR(10);








