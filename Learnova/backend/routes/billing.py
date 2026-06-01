from fastapi import APIRouter, Depends, HTTPException
from backend.models.user import UpgradeRequest, PaymentConfirm
from backend.database.db import users_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


# ----------------------------- Billing Helpers -----------------------------
def _bad_request(detail: str) -> None:
    """Raise a standardized 400 HTTPException with unchanged detail schema."""
    raise HTTPException(status_code=400, detail=detail)


def _resolve_plan_details(plan_type: str) -> tuple[float, int]:
    """Return (amount, expiration_days) for a plan type or raise 400 error."""
    if plan_type == "monthly":
        return 12.99, 30
    if plan_type == "yearly":
        return 99.99, 365
    _bad_request("Invalid plan type")


# ----------------------------- Billing Endpoints -----------------------------
@router.get("/status")
async def get_billing_status(
    current_user: dict = Depends(get_current_user)
):
    """Return current user tier and plan information."""
    return {
        "tier": current_user.get("tier", "free"),
        "plan_type": current_user.get("plan_type", ""),
        "plan_started": str(current_user.get("plan_started", "")),
        "plan_expires": str(current_user.get("plan_expires", "")),
    }


@router.post("/upgrade")
async def initiate_upgrade(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Return payment summary before final confirmation step."""
    if current_user.get("tier") == "pro":
        _bad_request("Already on Pro plan")

    amount, expires_days = _resolve_plan_details(request.plan_type)

    return {
        "plan_type": request.plan_type,
        "amount": amount,
        "currency": "USD",
        "expires_in_days": expires_days,
        "summary": (
            f"Learnova Pro "
            f"({'Monthly' if request.plan_type == 'monthly' else 'Yearly'}) "
            f"— ${amount}"
        )
    }


@router.post("/confirm")
async def confirm_payment(
    payment: PaymentConfirm,
    current_user: dict = Depends(get_current_user)
):
    """
    MOCK payment confirmation.
    In production this would verify with a payment gateway.
    For now: always succeeds and upgrades user to Pro.
    NEVER stores full card number — only last 4 digits.
    """
    amount, expires_days = _resolve_plan_details(payment.plan_type)

    now = datetime.utcnow()
    expires = now + timedelta(days=expires_days)

    # Update user in MongoDB — only last 4 digits of card are stored
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "tier": "pro",
            "plan_type": payment.plan_type,
            "plan_started": now,
            "plan_expires": expires,
            "card_last4": payment.card_last4,
        }}
    )

    # Send Pro welcome email in background
    try:
        from backend.services.email_service import send_pro_welcome_email
        import asyncio
        email = current_user.get("email", "")
        name = current_user.get("name", current_user.get("username", "Learner"))
        asyncio.ensure_future(send_pro_welcome_email(email, name, payment.plan_type))
    except Exception:
        pass

    return {
        "success": True,
        "message": "Payment successful",
        "tier": "pro",
        "plan_type": payment.plan_type,
        "amount_paid": amount,
        "currency": "USD",
        "plan_expires": expires.isoformat(),
    }


@router.post("/downgrade")
async def downgrade_to_free(
    current_user: dict = Depends(get_current_user)
):
    """Downgrade current user from Pro back to Free tier."""
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "tier": "free",
            "plan_type": "",
            "plan_started": None,
            "plan_expires": None,
        }}
    )
    return {
        "success": True,
        "message": "Downgraded to Free plan",
        "tier": "free"
    }
