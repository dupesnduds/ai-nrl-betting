from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import stripe
import os

from . import storage
from . import payments

app = FastAPI(title="Purchase Service API")

# --- CORS Middleware Configuration ---
origins = [
    "http://localhost:3001", # React frontend origin (adjust port if necessary)
    # Add other origins if needed, e.g., deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allow cookies/auth headers
    allow_methods=["*"],    # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allow all headers (including Authorization)
)

class StripePurchaseRequest(BaseModel):
    firebase_uid: str
    product_id: str  # e.g., "deep_dive_weekly"
    token: str       # Stripe payment token/id

class CouponPurchaseRequest(BaseModel):
    firebase_uid: str
    coupon_code: str

class OneTimeCodeRequest(BaseModel):
    session_id: str
    one_time_code: str

class PurchaseStatusResponse(BaseModel):
    has_access: bool
    tier: Optional[str] = None
    expires_at: Optional[str] = None

@app.post("/purchase/stripe")
async def purchase_with_stripe(req: StripePurchaseRequest):
    # Placeholder: verify payment with Stripe
    success, tier, expires_at = payments.verify_stripe_payment(req.firebase_uid, req.product_id, req.token)
    if not success:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    storage.grant_access(req.firebase_uid, tier, expires_at)
    return {"status": "success", "tier": tier, "expires_at": expires_at}

@app.post("/purchase/coupon")
async def purchase_with_coupon(req: CouponPurchaseRequest):
    valid, tier, expires_at = storage.redeem_coupon(req.firebase_uid, req.coupon_code)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired coupon code")
    storage.grant_access(req.firebase_uid, tier, expires_at)
    return {"status": "success", "tier": tier, "expires_at": expires_at}

@app.post("/purchase/one-time")
async def redeem_one_time_code(req: OneTimeCodeRequest):
    valid, expires_at = storage.redeem_one_time_code(req.session_id, req.one_time_code)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired one-time code")
    return {"status": "success", "expires_at": expires_at}

@app.get("/purchase/status", response_model=PurchaseStatusResponse)
async def get_purchase_status(firebase_uid: Optional[str] = None, session_id: Optional[str] = None):
    if firebase_uid:
        has_access, tier, expires_at = storage.check_access(firebase_uid=firebase_uid)
    elif session_id:
        has_access, tier, expires_at = storage.check_access(session_id=session_id)
    else:
        raise HTTPException(status_code=400, detail="Must provide firebase_uid or session_id")
    return PurchaseStatusResponse(has_access=has_access, tier=tier, expires_at=expires_at)
