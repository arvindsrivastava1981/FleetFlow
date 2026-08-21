-- ============================================================================
-- Incremental script for databases already created from an older schema.sql and this will have only ddl Statements to bring the database up to date with the latest schema.sql.
--

-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_trip_code_fkey;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_trip_code_fkey
        FOREIGN KEY (trip_code) REFERENCES trips(trip_code) ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- SETTLEMENT_TRANSFER expense type (driver-initiated settlement closing entry).
-- The inline CHECK in older schema.sql builds auto-name `expenses_exp_type_check`;
-- swap it idempotently so legacy databases accept the new ledger row type.
-- ----------------------------------------------------------------------------
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_exp_type_check
        CHECK (exp_type IN ('FUEL', 'DEF', 'TOLL', 'REPAIR', 'CHALLAN', 'MISC',
                            'GOODS_BUY', 'GOODS_SALE', 'CASH_ADVANCE',
                            'DRIVER_SALARY', 'SETTLEMENT_TRANSFER'));









