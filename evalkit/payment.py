"""Payment routes for EvalKit v2 - PayPal, Razorpay, Payoneer.

All payment flows follow this pattern:
1. Frontend calls /create-order -> gets order_id + approval_url
2. User completes payment on provider's page
3. Frontend calls /capture or /verify -> we confirm with provider + activate subscription
4. Webhook provides backup confirmation (in case user closes browser mid-payment)
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from evalkit.auth import get_current_user_id
from evalkit.config import settings
from evalkit.subscriptions import TIER_CONFIGS, PAID_TIERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/payments", tags=["payments"])


# --- Pydantic Models ---

class CreateOrderRequest(BaseModel):
    tier: str
    provider: str
    terms_accepted: bool = False

class OrderResponse(BaseModel):
    order_id: str
    approval_url: Optional[str] = None
    provider: str
    tier: str
    amount_usd: float

class CaptureRequest(BaseModel):
    order_id: str

class RazorpayVerifyRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class SubscriptionStatusResponse(BaseModel):
    user_id: str
    tier: str
    evaluations_used: int
    evaluations_limit: int
    evaluations_remaining: int
    subscription_expires_at: Optional[str] = None

class TierInfoResponse(BaseModel):
    tiers: dict


# --- Helpers ---

def _validate_paid_tier(tier: str) -> dict:
    config = PAID_TIERS.get(tier)
    if not config:
        raise HTTPException(400, f"Invalid tier for payment: '{tier}'. Valid paid tiers: {list(PAID_TIERS.keys())}")
    return config


def _get_db():
    from evalkit.main import get_db
    return get_db()


async def _activate_subscription(user_id: str, tier: str, provider: str,
                                  order_id: str, amount: float,
                                  payment_id: str = None, currency: str = "USD"):
    db = _get_db()
    from evalkit.storage.sqlite import (
        create_subscription, update_payment_status, ensure_user
    )
    await ensure_user(db, user_id)
    await update_payment_status(
        db, provider_order_id=order_id, status="captured",
        provider_payment_id=payment_id,
        metadata=json.dumps({"provider": provider, "tier": tier}),
    )
    sub = await create_subscription(
        db, user_id=user_id, tier=tier, provider=provider,
        payment_id=payment_id or order_id, amount=amount, currency=currency,
        duration_days=30,
    )
    logger.info(f"Subscription activated: user={user_id} tier={tier} provider={provider} order={order_id}")
    return sub


# --- PayPal Token Cache ---

_paypal_token_cache: dict = {"token": None, "expires_at": 0}


async def _paypal_access_token() -> str:
    now = time.time()
    if _paypal_token_cache["token"] and _paypal_token_cache["expires_at"] > now + 60:
        return _paypal_token_cache["token"]

    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise HTTPException(503, "PayPal not configured")

    base = _paypal_base_url()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{base}/v1/oauth2/token",
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()

    _paypal_token_cache["token"] = data["access_token"]
    _paypal_token_cache["expires_at"] = now + data.get("expires_in", 32400)
    return data["access_token"]


def _paypal_base_url() -> str:
    return "https://api-m.sandbox.paypal.com" if settings.paypal_mode == "sandbox" else "https://api-m.paypal.com"


# --- PayPal Routes ---

@router.post("/paypal/create-order", response_model=OrderResponse)
async def paypal_create_order(req: CreateOrderRequest, user_id: str = Depends(get_current_user_id)):
    if not req.terms_accepted:
        raise HTTPException(400, "You must accept the Terms of Service and Privacy Policy before proceeding with payment.")
    tier_cfg = _validate_paid_tier(req.tier)
    amount = tier_cfg["price_usd"]

    token = await _paypal_access_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_paypal_base_url()}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": f"{amount:.2f}"},
                    "description": f"EvalKit {req.tier.title()} Plan - Monthly",
                    "custom_id": f"{user_id}|{req.tier}",
                }],
                "application_context": {
                    "return_url": f"{settings.frontend_url}/payment/success",
                    "cancel_url": f"{settings.frontend_url}/payment/cancel",
                    "brand_name": "EvalKit",
                    "user_action": "PAY_NOW",
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()

    db = _get_db()
    from evalkit.storage.sqlite import create_payment_transaction
    await create_payment_transaction(db, user_id, "paypal", data["id"], req.tier, amount)

    approval_url = next((l["href"] for l in data.get("links", []) if l["rel"] == "approve"), None)
    return OrderResponse(
        order_id=data["id"], approval_url=approval_url,
        provider="paypal", tier=req.tier, amount_usd=amount,
    )


@router.post("/paypal/capture")
async def paypal_capture(req: CaptureRequest, user_id: str = Depends(get_current_user_id)):
    token = await _paypal_access_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_paypal_base_url()}/v2/checkout/orders/{req.order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code not in (200, 201):
            logger.error(f"PayPal capture failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, "Payment capture failed")
        data = resp.json()

    custom_id = ""
    try:
        custom_id = data["purchase_units"][0]["payments"]["captures"][0].get("custom_id", "")
    except (KeyError, IndexError):
        pass
    parts = custom_id.split("|") if custom_id else []
    tier = parts[1] if len(parts) == 2 else None

    if not tier:
        db = _get_db()
        from evalkit.storage.sqlite import get_payment_by_order_id
        txn = await get_payment_by_order_id(db, req.order_id)
        tier = txn["tier"] if txn else "basic"

    amount = float(data.get("purchase_units", [{}])[0].get("amount", {}).get("value", 0))
    capture_id = ""
    try:
        capture_id = data["purchase_units"][0]["payments"]["captures"][0]["id"]
    except (KeyError, IndexError):
        pass

    sub = await _activate_subscription(
        user_id=user_id, tier=tier, provider="paypal",
        order_id=req.order_id, amount=amount, payment_id=capture_id,
    )
    return {"status": "captured", "order_id": req.order_id, "tier": tier, "subscription": sub}


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    body = await request.json()
    event_type = body.get("event_type", "")
    logger.info(f"PayPal webhook received: {event_type}")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        resource = body.get("resource", {})
        custom_id = resource.get("custom_id", "")
        parts = custom_id.split("|") if custom_id else []
        if len(parts) == 2:
            user_id, tier = parts
            amount = float(resource.get("amount", {}).get("value", 0))
            order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id", "")
            capture_id = resource.get("id", "")
            try:
                await _activate_subscription(
                    user_id=user_id, tier=tier, provider="paypal",
                    order_id=order_id, amount=amount, payment_id=capture_id,
                )
            except Exception as e:
                logger.error(f"PayPal webhook activation failed: {e}")

    return {"status": "ok"}


# --- Razorpay Routes ---

@router.post("/razorpay/create-order", response_model=OrderResponse)
async def razorpay_create_order(req: CreateOrderRequest, user_id: str = Depends(get_current_user_id)):
    if not req.terms_accepted:
        raise HTTPException(400, "You must accept the Terms of Service and Privacy Policy before proceeding with payment.")
    try:
        import razorpay
    except ImportError:
        raise HTTPException(503, "Razorpay SDK not installed. Run: pip install razorpay")

    tier_cfg = _validate_paid_tier(req.tier)
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(503, "Razorpay not configured")

    amount = tier_cfg["price_usd"]
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    order = client.order.create({
        "amount": int(amount * 100),
        "currency": "USD",
        "notes": {"user_id": user_id, "tier": req.tier},
    })

    db = _get_db()
    from evalkit.storage.sqlite import create_payment_transaction
    await create_payment_transaction(db, user_id, "razorpay", order["id"], req.tier, amount)

    return OrderResponse(
        order_id=order["id"], provider="razorpay",
        tier=req.tier, amount_usd=amount,
    )


@router.post("/razorpay/verify")
async def razorpay_verify(req: RazorpayVerifyRequest, user_id: str = Depends(get_current_user_id)):
    try:
        import razorpay
    except ImportError:
        raise HTTPException(503, "Razorpay SDK not installed")

    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(503, "Razorpay not configured")

    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": req.order_id,
            "razorpay_payment_id": req.payment_id,
            "razorpay_signature": req.signature,
        })
    except Exception:
        raise HTTPException(400, "Invalid payment signature")

    db = _get_db()
    from evalkit.storage.sqlite import get_payment_by_order_id
    txn = await get_payment_by_order_id(db, req.order_id)
    tier = txn["tier"] if txn else "basic"
    amount = txn["amount_usd"] if txn else 0

    sub = await _activate_subscription(
        user_id=user_id, tier=tier, provider="razorpay",
        order_id=req.order_id, amount=amount, payment_id=req.payment_id,
    )
    return {"status": "verified", "payment_id": req.payment_id, "tier": tier, "subscription": sub}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    body_bytes = await request.body()
    body = json.loads(body_bytes)
    event = body.get("event", "")
    logger.info(f"Razorpay webhook received: {event}")

    if settings.razorpay_webhook_secret:
        signature = request.headers.get("x-razorpay-signature", "")
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Razorpay webhook signature mismatch")
            raise HTTPException(400, "Invalid webhook signature")

    if event == "payment.captured":
        payload = body.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payload.get("notes", {})
        user_id = notes.get("user_id")
        tier = notes.get("tier")
        order_id = payload.get("order_id")
        payment_id = payload.get("id")
        amount = payload.get("amount", 0) / 100

        if user_id and tier and order_id:
            try:
                await _activate_subscription(
                    user_id=user_id, tier=tier, provider="razorpay",
                    order_id=order_id, amount=amount, payment_id=payment_id,
                )
            except Exception as e:
                logger.error(f"Razorpay webhook activation failed: {e}")

    return {"status": "ok"}


# --- Payoneer Routes ---

@router.post("/payoneer/create-checkout", response_model=OrderResponse)
async def payoneer_create_checkout(req: CreateOrderRequest, user_id: str = Depends(get_current_user_id)):
    if not req.terms_accepted:
        raise HTTPException(400, "You must accept the Terms of Service and Privacy Policy before proceeding with payment.")
    tier_cfg = _validate_paid_tier(req.tier)
    if not settings.payoneer_api_key:
        raise HTTPException(503, "Payoneer not configured")

    amount = tier_cfg["price_usd"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.payoneer.com/v4/checkout",
            headers={
                "Authorization": f"Bearer {settings.payoneer_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "amount": amount,
                "currency": "USD",
                "description": f"EvalKit {req.tier.title()} Plan - Monthly",
                "country": "US",
                "returnUrl": f"{settings.frontend_url}/payment/success?provider=payoneer&tier={req.tier}",
                "cancelUrl": f"{settings.frontend_url}/payment/cancel",
                "notificationUrl": f"{settings.frontend_url}/v1/payments/webhooks/payoneer",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    order_id = data.get("id", "")

    db = _get_db()
    from evalkit.storage.sqlite import create_payment_transaction
    await create_payment_transaction(db, user_id, "payoneer", order_id, req.tier, amount)

    return OrderResponse(
        order_id=order_id,
        approval_url=data.get("redirect_url"),
        provider="payoneer",
        tier=req.tier,
        amount_usd=amount,
    )


# --- Status & Info ---

@router.get("/status", response_model=SubscriptionStatusResponse)
async def payment_status(user_id: str = Depends(get_current_user_id)):
    db = _get_db()
    from evalkit.storage.sqlite import get_user, get_active_subscription, ensure_user
    from evalkit.subscriptions import check_quota

    user = await get_user(db, user_id)
    if not user:
        user = await ensure_user(db, user_id)

    quota = await check_quota(user_id, db)
    sub = await get_active_subscription(db, user_id)

    return SubscriptionStatusResponse(
        user_id=user_id,
        tier=user["tier"],
        evaluations_used=quota["used"],
        evaluations_limit=quota["limit"],
        evaluations_remaining=quota["remaining"],
        subscription_expires_at=sub["expires_at"] if sub else None,
    )


@router.get("/tiers", response_model=TierInfoResponse)
async def list_tiers():
    return TierInfoResponse(tiers=TIER_CONFIGS)


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user_id)):
    db = _get_db()
    from evalkit.storage.sqlite import get_user, get_active_subscription, ensure_user
    from evalkit.subscriptions import check_quota

    user = await get_user(db, user_id)
    if not user:
        user = await ensure_user(db, user_id)

    quota = await check_quota(user_id, db)
    sub = await get_active_subscription(db, user_id)

    return {
        "user": {k: v for k, v in user.items() if k != "updated_at"},
        "subscription": sub,
        "quota": quota,
    }
