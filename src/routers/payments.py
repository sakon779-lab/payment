"""SCRUM-5: Create Payment Intent & Rate Locking.

POST /api/v1/payments — fetch the current exchange rate server-side, compute the
crypto amount with a 1% buffer rounded UP to 6 decimals, allocate a one-time
wallet address, and return a 15-minute TTL. Idempotent per order_id while the
existing PENDING intent has not expired.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.main import get_db
from src.models import PaymentTransaction
from src.services.rate_source import fetch_rate, RateUnavailable

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

SUPPORTED_TOKENS = ("USDT", "USDC")
SUPPORTED_NETWORKS = ("POLYGON", "ETHEREUM", "BSC")
TTL_MINUTES = 15
BUFFER = Decimal("1.01")
_PAY_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


class PaymentIntentRequest(BaseModel):
    # All fields optional; validated explicitly in the route body so each error
    # detail string is raised by an explicit HTTPException (per design contract).
    # fiat_amount is Any so a non-numeric value reaches the route (-> 400) rather
    # than being rejected by pydantic (-> 422).
    order_id: str | None = None
    fiat_amount: Any | None = None
    fiat_currency: str | None = None
    token_symbol: str | None = None
    network: str | None = None


class PaymentIntentResponse(BaseModel):
    payment_id: str
    wallet_address: str
    crypto_amount: str
    exchange_rate: str
    expires_at: str
    status: str


def compute_crypto_amount(fiat_amount: float, exchange_rate: float) -> str:
    """Pure pricing rule: (fiat / rate) * 1.01, rounded UP to 6 decimals."""
    raw = (Decimal(str(fiat_amount)) / Decimal(str(exchange_rate))) * BUFFER
    crypto = raw.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
    return f"{crypto:.6f}"


def _format_rate(exchange_rate: float) -> str:
    return f"{Decimal(str(exchange_rate)).quantize(Decimal('0.01')):.2f}"


def _payment_id_for(order_id: str, row_id: int) -> str:
    """Deterministic PAY-<uuid> so a replay returns the SAME payment_id."""
    return "PAY-" + str(uuid.uuid5(_PAY_NAMESPACE, f"{order_id}:{row_id}"))


def _generate_wallet_address() -> str:
    """One-time HD-wallet address (Phase 1 placeholder)."""
    return "0x" + uuid.uuid4().hex[:40]


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.post("", response_model=PaymentIntentResponse, status_code=201)
async def create_payment_intent(
    request: PaymentIntentRequest,
    db: Session = Depends(get_db),
):
    # Validation order: order_id -> fiat_amount -> fiat_currency -> token -> network
    order_id = request.order_id
    if order_id is None or str(order_id).strip() == "":
        raise HTTPException(status_code=400, detail="Order ID is required")

    if request.fiat_amount is None:
        raise HTTPException(status_code=400, detail="Fiat amount is required")
    try:
        fiat_amount = float(request.fiat_amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Fiat amount must be a number")
    if fiat_amount <= 0:
        raise HTTPException(status_code=400, detail="Fiat amount must be greater than zero")

    if request.fiat_currency is None:
        raise HTTPException(status_code=400, detail="Fiat currency is required")
    if request.fiat_currency != "THB":
        raise HTTPException(status_code=400, detail="Unsupported Currency")

    if request.token_symbol is None:
        raise HTTPException(status_code=400, detail="Token symbol is required")
    if request.token_symbol not in SUPPORTED_TOKENS:
        raise HTTPException(status_code=400, detail="Unsupported Currency")

    if request.network is None:
        raise HTTPException(status_code=400, detail="Network is required")
    if request.network not in SUPPORTED_NETWORKS:
        raise HTTPException(status_code=400, detail="Unsupported Network")

    now = datetime.now(timezone.utc)

    # Idempotency: reuse an existing non-expired PENDING intent for this order_id.
    existing = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.status == "PENDING",
            PaymentTransaction.expires_at > now,
        )
        .order_by(PaymentTransaction.id.desc())
        .first()
    )
    if existing is not None:
        crypto_amount = f"{Decimal(str(existing.amount_expected)):.6f}"
        # Recover the locked rate from the stored amount (rounding error is far
        # below the 2-decimal rendering precision).
        recovered_rate = fiat_amount / (float(existing.amount_expected) / float(BUFFER))
        return PaymentIntentResponse(
            payment_id=_payment_id_for(order_id, existing.id),
            wallet_address=existing.payment_address,
            crypto_amount=crypto_amount,
            exchange_rate=_format_rate(recovered_rate),
            expires_at=_iso_utc(existing.expires_at),
            status=existing.status,
        )

    # Fetch the rate server-side (upstream of the pure rule).
    try:
        exchange_rate = await fetch_rate(
            token_symbol=request.token_symbol,
            network=request.network,
            fiat_currency=request.fiat_currency,
        )
    except RateUnavailable:
        raise HTTPException(status_code=502, detail="Exchange rate unavailable")

    crypto_amount = compute_crypto_amount(fiat_amount, exchange_rate)
    expires_at = now + timedelta(minutes=TTL_MINUTES)
    wallet_address = _generate_wallet_address()

    row = PaymentTransaction(
        order_id=order_id,
        payment_address=wallet_address,
        amount_expected=Decimal(crypto_amount),
        status="PENDING",
        expires_at=expires_at,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return PaymentIntentResponse(
        payment_id=_payment_id_for(order_id, row.id),
        wallet_address=wallet_address,
        crypto_amount=crypto_amount,
        exchange_rate=_format_rate(exchange_rate),
        expires_at=_iso_utc(expires_at),
        status="PENDING",
    )