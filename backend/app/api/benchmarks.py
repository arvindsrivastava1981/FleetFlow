"""Benchmarks router — manage fuel benchmarks.

Provides CRUD operations for per-state fuel price benchmarks.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.config import settings
from backend.app.core.security import require_admin
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    get_all_benchmarks,
    get_benchmark_by_id,
    insert_benchmark,
    update_benchmark,
    delete_benchmark,
)

router = APIRouter()


@router.get("/fuel-benchmarks")
def list_fuel_benchmarks(request: Request) -> list[dict]:
    """List all fuel benchmarks."""
    guard = require_admin(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        return get_all_benchmarks(conn)


@router.post("/fuel-benchmarks")
def add_fuel_benchmark(request: Request, state_code: str = None, state_name: str = None,
                    benchmark_price_per_liter: float = None, tolerance_pct: float = 8.0) -> dict:
    """Create a new fuel benchmark."""
    guard = require_admin(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        new_id = insert_benchmark(conn, state_code or "", state_name or "",
                                 benchmark_price_per_liter or 0.0, tolerance_pct or 8.0)
        return {"id": new_id, "message": "Benchmark added successfully"}


@router.put("/fuel-benchmarks/{id}")
def update_fuel_benchmark(request: Request, id: int, state_code: str = None, state_name: str = None,
                        benchmark_price_per_liter: float = None, tolerance_pct: float = 8.0) -> dict:
    """Update a fuel benchmark."""
    guard = require_admin(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        updated = update_benchmark(conn, id,
                                  state_code or "", state_name or "",
                                  benchmark_price_per_liter or 0.0,
                                  tolerance_pct or 8.0)
        return {"id": id, "message": "Benchmark updated successfully" if updated else "Benchmark not found"}


@router.delete("/fuel-benchmarks/{id}")
def delete_fuel_benchmark(request: Request, id: int) -> dict:
    """Delete a fuel benchmark."""
    guard = require_admin(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        removed = delete_benchmark(conn, id)
        return {"id": id, "message": "Benchmark deleted successfully" if removed else "Benchmark not found"}