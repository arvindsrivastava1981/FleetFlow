"""Data models / domain access layer.

Thin, row-shaped helpers that wrap raw `db/queries` SQL so services and
routers never hand-write SQL or touch raw cursors. Each class corresponds to
a core table:

- Fleet      -> `fleets`
- Vehicle    -> `vehicles`
- Trip       -> `trips`
- Expense    -> `expenses`
- FuelBenchmark -> `fuel_benchmarks`
- TollCorridor  -> `toll_corridors` (Phase B)

Type annotations (TripCode, ExpenseType, ManagerStatus, TripStatus) mirror the
DB CHECK constraints in /database/schema.sql so the domain can't drift.
"""