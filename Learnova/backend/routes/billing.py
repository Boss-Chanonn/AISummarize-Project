from fastapi import APIRouter, Depends, HTTPException
from backend.models.user import UpgradeRequest, PaymentConfirm
from backend.database.db import users_collection
from backend.middleware.auth_middleware import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId
import os

router = APIRouter()


@router.get("/status")
async def get_billing_status(
    current_user: dict = Depends(get_current_user)
):
    """Return current user tier and plan info"""
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
    """Return payment summary before confirmation"""
    if current_user.get("tier") == "pro":
        raise HTTPException(
            status_code=400,
            detail="Already on Pro plan"
        )

    if request.plan_type == "monthly":
        amount = 12.99
        expires_days = 30
    elif request.plan_type == "yearly":
        amount = 99.99
        expires_days = 365
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan type"
        )

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
    if payment.plan_type == "monthly":
        amount = 12.99
        expires_days = 30
    elif payment.plan_type == "yearly":
        amount = 99.99
        expires_days = 365
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan type"
        )

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
    """Allow user to cancel Pro and return to Free"""
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
