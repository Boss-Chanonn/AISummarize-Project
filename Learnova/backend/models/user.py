from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    dob: str           # required — format YYYY-MM-DD
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    role: str = "user"
    tier: str = "free"
    dob: Optional[str] = None
    phone: Optional[str] = None

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class AdminUpdateProfile(BaseModel):
    name          : Optional[str]      = None
    email         : Optional[EmailStr] = None
    phone         : Optional[str]      = None
    dob           : Optional[str]      = None   # YYYY-MM-DD

class AdminUpdateAccount(BaseModel):
    role          : Optional[str]      = None   # user | admin
    tier          : Optional[str]      = None   # free | pro
    status        : Optional[str]      = None   # active | inactive

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# ── Billing / Plan models ──────────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan_type: str  # "monthly" or "yearly"

class PaymentConfirm(BaseModel):
    plan_type: str
    card_name: str
    card_last4: str     # last 4 digits only — NEVER store full card number
    amount: float
    currency: str = "USD"

class BillingResponse(BaseModel):
    tier: str
    plan_type: str
    plan_started: Optional[str] = None
    plan_expires: Optional[str] = None
    amount_paid: Optional[float] = None
