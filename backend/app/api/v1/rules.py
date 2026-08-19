from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.config import settings
from backend.app.core.security import require_json_auth

from backend.app.api.v1.deps import _ok
from backend.app.schemas.api_v1 import Data, RulesData

router = APIRouter(prefix="/api/v1")


@router.get("/rules", response_model=Data[RulesData])
def api_rules(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    rules = {
        "FUEL": [
            "Math integrity: flags if Amount differs from Liters x Rate by more than Rs 10.",
            f"Price benchmark: rate must be inside base Rs {settings.benchmark_price}/L band.",
            f"Tank capacity: claimed liters can not exceed {settings.tank_capacity_liters:.0f}L.",
            "Odometer rollback: flags if new reading is lower than the previous fuel reading.",
            f"Mileage check: km/L below {settings.expected_kml:.1f} x 70% is flagged.",
        ],
        "TOLL": [
            "Always flagged", "Cash toll claims disallowed on FASTag corridors.",
        ],
        "REPAIR": [
            "Any repair claim above Rs 3,000 requires owner pre-approval.",
        ],
        "CHALLAN": [
            "Always flagged; verified against the e-challan portal.",
        ],
        "DEF": [
            f"Price benchmark: rate above Rs {settings.def_rate_max:.0f}/l ceiling is flagged.",
            f"Consumption ratio: DEF outside {settings.def_min_ratio_pct:.0f}%-{settings.def_max_ratio_pct:.0f}% of diesel is flagged.",
        ],
    }
    return _ok(rules)