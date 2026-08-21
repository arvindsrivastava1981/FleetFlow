from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Data(BaseModel, Generic[T]):
    """Generic `{ "data": <payload> }` envelope used by most endpoints."""

    data: T


# ---------------------------------------------------------------------------#
# Auth
# ---------------------------------------------------------------------------#
class AuthUser(BaseModel):
    id: int
    username: str
    role: str


class AuthMe(BaseModel):
    """`GET /auth/me` — no `data` wrapper (client reads `user` directly)."""

    user: AuthUser


class LoginResult(BaseModel):
    """`POST /auth/login` — no `data` wrapper (client reads token/user)."""

    token: str
    user: AuthUser
    landing: str


class LogoutResult(BaseModel):
    logged_out: bool


class ChangePasswordResult(BaseModel):
    id: int
    password_changed: bool


# ---------------------------------------------------------------------------#
# Dashboard
# ---------------------------------------------------------------------------#
class DashboardOverview(BaseModel):
    """Role-aware overview payload (extra keys vary by role)."""

    model_config = ConfigDict(extra="allow")

    role: str


# ---------------------------------------------------------------------------#
# Trips & settlements
# ---------------------------------------------------------------------------#
class TripRow(BaseModel):
    """A `trips.*` row plus the per-trip `stats` dict attached by the route."""

    model_config = ConfigDict(extra="allow")

    trip_code: Optional[str] = None


class TripStats(BaseModel):
    """Aggregated stats for a trip (attached as `stats` on list rows)."""

    model_config = ConfigDict(extra="allow")


class TripListItem(BaseModel):
    """Trip listing item: a trip row plus its stats."""

    model_config = ConfigDict(extra="allow")

    stats: Optional[TripStats] = None


class SettlementSummary(BaseModel):
    """The computed settlement block on trip detail."""

    model_config = ConfigDict(extra="allow")

    advance_amount: float = 0.0
    driver_batta: float = 0.0
    net_balance: float = 0.0
    is_driver_refund: bool = False
    status_label_en: str = ""
    status_label_hi: str = ""


class TripDetailData(BaseModel):
    """`GET /trips/{code}` payload: trip, its expenses, and the settlement."""

    model_config = ConfigDict(extra="allow")

    trip: dict[str, Any]
    expenses: list[Any] = Field(default_factory=list)


class CreateTripResult(BaseModel):
    trip_code: str
    status: str


class SettleTripResult(BaseModel):
    trip_code: str
    status: str


class DriverSalarySummary(BaseModel):
    """Per-trip batta/settlement line on the driver salary view."""

    model_config = ConfigDict(extra="allow")

    trip_code: str


class DriverSalaryTotals(BaseModel):
    total_batta: float
    total_payable: float
    total_refund: float


class DriverSalary(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    trips: list[DriverSalarySummary] = Field(default_factory=list)
    totals: DriverSalaryTotals


# ---------------------------------------------------------------------------#
# Expenses & escalations
# ---------------------------------------------------------------------------#
class ExpenseAccepted(BaseModel):
    accepted: bool
    trip_code: str
    exp_type: str
    manager_status: str
    is_flagged: bool
    flag_reason: Optional[str] = None


class ExpenseActionResult(BaseModel):
    expense_id: int
    status: str
    trip_code: str
    label_en: Optional[str] = None
    label_hi: Optional[str] = None


class EscalationRow(BaseModel):
    """A flagged/pending expense row in the WhatsApp escalation feed."""

    model_config = ConfigDict(extra="allow")

    is_flagged: bool = False


# ---------------------------------------------------------------------------#
# Benchmarks
# ---------------------------------------------------------------------------#
class BenchmarkRow(BaseModel):
    model_config = ConfigDict(extra="allow")


class ResourceAck(BaseModel):
    """Generic `{ "id": N }` acknowledgement for created/updated rows."""

    id: int


class ToggleAck(BaseModel):
    id: int
    is_active: bool


# ---------------------------------------------------------------------------#
# Billing
# ---------------------------------------------------------------------------#
class Plan(BaseModel):
    code: str
    name: str
    price: int
    period: str
    vehicle_limit: int
    description: str


class FleetBilling(BaseModel):
    """Billing-overview fleet block (extra keys allowed)."""

    model_config = ConfigDict(extra="allow")

    name: str = "Your Fleet"


class BillingOverview(BaseModel):
    fleet: FleetBilling
    plans: list[Plan]


class BillingSubscribeResult(BaseModel):
    redirect_url: Optional[str] = None
    activated: bool = True
    trial: bool = False
    payment_link: Optional[dict[str, Any]] = None


class BillingVehicleSlotResult(BaseModel):
    redirect_url: Optional[str] = None
    payment_link: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------#
# Rules engine
# ---------------------------------------------------------------------------#
class RulesData(BaseModel):
    """`GET /rules` — { rule-group: [explanations...] }."""

    model_config = ConfigDict(extra="allow")