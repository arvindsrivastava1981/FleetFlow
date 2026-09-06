from __future__ import annotations

import re as _re
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Data(BaseModel, Generic[T]):
    """Generic `{ "data": <payload> }` envelope used by most endpoints."""

    data: T


# ---------------------------------------------------------------------------#
# Auth
# ---------------------------------------------------------------------------#
class AuthUser(BaseModel):
    id: int
    email: str
    role: str
    full_name: Optional[str] = None
    fleet_id: Optional[int] = None
    auth_provider: Optional[str] = None
    email_verified: Optional[bool] = None


class AuthMe(BaseModel):
    """`GET /auth/me` — no `data` wrapper (client reads `user` directly)."""

    user: AuthUser
    expires_at: Optional[int] = None  # epoch seconds (audit E-10)


class SessionRefreshResult(BaseModel):
    """`POST /auth/refresh` — new sliding expiry (audit E-10)."""

    expires_at: int


class LoginResult(BaseModel):
    """`POST /auth/login` — no `data` wrapper (client reads token/user)."""

    token: str
    user: AuthUser
    landing: str


class LogoutResult(BaseModel):
    logged_out: bool


# ---------------------------------------------------------------------------#
# Auth: registration & verification
# ---------------------------------------------------------------------------#
class RegisterRequest(BaseModel):
    """`POST /auth/register` payload.

    `username` was removed (email is the unique login key); display `full_name`
    is now auto-derived from the email local-part by the endpoint.
    """

    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: str
    confirm_password: str


class RegisterResponse(BaseModel):
    message: str


class VerifyResponse(BaseModel):
    message: str


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
class TripStats(BaseModel):
    """Aggregated stats for a trip (attached as `stats` on list rows)."""

    model_config = ConfigDict(extra="allow")


class TripListItem(BaseModel):
    """Trip listing item: a trip row plus its stats."""

    model_config = ConfigDict(extra="allow")

    stats: Optional[TripStats] = None


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
    expense_id: Optional[int] = None
    trip_code: str
    exp_type: str
    manager_status: str
    is_flagged: bool
    flag_reason: Optional[str] = None
    # SETTLEMENT_TRANSFER only: the server-computed |net_balance| recorded as
    # the closing-entry amount (client-supplied amounts are ignored).
    settlement_amount: Optional[float] = None
    # True when a receipt photo was attached (stored as a data URL).
    has_receipt: bool = False


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
class BenchmarkFavoriteAck(BaseModel):
    """`POST/DELETE /benchmarks/{state_code}/favorite` acknowledgement."""

    state_code: str
    is_favorite: bool


class HomeStateResult(BaseModel):
    """`PUT /benchmarks/home-state` — the caller's usual operating state."""

    home_state_code: Optional[str] = None


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
    price: Optional[int] = None
    period: Optional[str] = None
    vehicle_limit: Optional[int] = None
    trial_days: Optional[int] = None
    description: str = ""


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


# ---------------------------------------------------------------------------#
# Contact
# ---------------------------------------------------------------------------#
class ContactRequest(BaseModel):
    """`POST /contact` payload — public, unauthenticated contact form."""

    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=20)
    firm: Optional[str] = Field(default=None, max_length=120)
    message: str = Field(..., min_length=1, max_length=3000)
    # Honeypot anti-bot field — must remain empty. If filled, the submission
    # is from a bot and is silently accepted without sending email.
    website: Optional[str] = Field(default=None)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("invalid email address")
        return v

    @field_validator("phone", "firm")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v or None
        return v


class ContactResponse(BaseModel):
    """`POST /contact` response."""

    sent: bool = False
    message: str = ""
