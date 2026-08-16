-- ----------------------------------------------------------------------------
-- FleetFlow Demo Data Cleanup
-- Removes the TRIP-101 demo trip and its expenses while retaining reference data.
-- ----------------------------------------------------------------------------

Truncate table fleets cascade;

truncate table vehicles cascade;
truncate table trips cascade;
truncate table expenses cascade;
truncate table fuel_benchmarks cascade;
