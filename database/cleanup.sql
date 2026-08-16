-- ----------------------------------------------------------------------------
-- FleetFlow Demo Data Cleanup
-- Removes the TRIP-101 demo trip and its expenses while retaining reference data.
-- ----------------------------------------------------------------------------
BEGIN;

DELETE FROM expenses
WHERE trip_code = 'TRIP-101';

DELETE FROM trips
WHERE trip_code = 'TRIP-101';

COMMIT;
