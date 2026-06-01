from pydantic import BaseModel, EmailStr
from typing import Optional


# ----------------------------- Auth Models -----------------------------
class UserCreate(BaseModel):
    """Request body used when a new user registers an account."""

    name: str
    email: EmailStr
    password: str
    dob: str           # required — format YYYY-MM-DD
    phone: Optional[str] = None


class UserLogin(BaseModel):
    """Request body used for email and password login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Serialized user payload returned inside auth responses."""

    id: Optional[str] = None
    name: str
    email: str
    role: str = "user"
    tier: str = "free"
    dob: Optional[str] = None
    phone: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT response payload that wraps the token and user profile."""

    token: str
    user: UserResponse


class UserUpdate(BaseModel):
    """Editable self-service profile fields for the current user."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


# ----------------------------- Admin Models -----------------------------
class AdminUpdateProfile(BaseModel):
    """Profile fields an admin may edit on behalf of a user."""

    name          : Optional[str]      = None
    email         : Optional[EmailStr] = None
    phone         : Optional[str]      = None
    dob           : Optional[str]      = None   # YYYY-MM-DD


class AdminUpdateAccount(BaseModel):
    """Account-level fields an admin may update for a user record."""

    role          : Optional[str]      = None   # user | admin
    tier          : Optional[str]      = None   # free | pro
    status        : Optional[str]      = None   # active | inactive


class PasswordChange(BaseModel):
    """Request body for changing a password after current-password verification."""

    current_password: str
    new_password: str


# ----------------------------- Billing Models -----------------------------

class UpgradeRequest(BaseModel):
    """Request body for selecting a billing plan before payment confirmation."""

    plan_type: str  # "monthly" or "yearly"


class PaymentConfirm(BaseModel):
    """Mock payment confirmation body used to upgrade a user to Pro."""

    plan_type: str
    card_name: str
    card_last4: str     # last 4 digits only — NEVER store full card number
    amount: float
    currency: str = "USD"


class BillingResponse(BaseModel):
    """Billing status payload returned by the billing endpoints."""

    tier: str
    plan_type: str
    plan_started: Optional[str] = None
    plan_expires: Optional[str] = None
    amount_paid: Optional[float] = None


# ----------------------------- Calendar Models -----------------------------

class CalendarConnection(BaseModel):
    """OAuth token data stored for one connected calendar provider."""

    provider: str                    # "google" | "outlook" | "apple"
    email: str                       # account email used for connection
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None  # unix timestamp
    connected_at: str = ""           # ISO datetime
    caldav_url: Optional[str] = None # Apple Calendar CalDAV


class CalendarEvent(BaseModel):
    """Payload for creating a calendar event from a study resource."""

    provider: str                    # "google" | "outlook" | "apple"
    title: str
    description: str = ""
    start_time: str                  # ISO datetime
    end_time: str                    # ISO datetime
    location: str = ""


class CalendarStatus(BaseModel):
    """Status of all calendar connections for a user."""

    google: bool = False
    google_email: str = ""
    outlook: bool = False
    outlook_email: str = ""
    apple: bool = False
    apple_email: str = ""
