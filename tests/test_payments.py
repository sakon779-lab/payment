"""Tests for SCRUM-5: Create Payment Intent & Rate Locking API."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main import app, SessionLocal
from src.models import PaymentTransaction
from src.routers import payments as payments_module
from src.services import rate_source

test_client = TestClient(app)

URL = "/api/v1/payments"


def _payload(**overrides):
    base = {
        "order_id": "ORD-12345",
        "fiat_amount": 1000.00,
        "fiat_currency": "THB",
        "token_symbol": "USDT",
        "network": "POLYGON",
    }
    base.update(overrides)
    return base


def _clear_payments():
    db = SessionLocal()
    db.query(PaymentTransaction).delete()
    db.commit()
    db.close()


def _count_rows(order_id):
    db = SessionLocal()
    n = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == order_id).count()
    db.close()
    return n


def test_create_payment_success():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        resp = test_client.post(URL, json=_payload(order_id="ORD-SUCCESS"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["crypto_amount"] == "28.450705"
    assert data["exchange_rate"] == "35.50"
    assert data["status"] == "PENDING"
    assert data["payment_id"].startswith("PAY-")
    assert data["wallet_address"].startswith("0x")
    assert data["expires_at"].endswith("Z")
    db = SessionLocal()
    row = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == "ORD-SUCCESS").first()
    assert row is not None
    assert row.status == "PENDING"
    db.close()


def test_crypto_amount_rounds_up():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=33.333333)):
        resp = test_client.post(URL, json=_payload(order_id="ORD-ROUND"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["crypto_amount"] == "30.300001"
    assert data["exchange_rate"] == "33.33"


def test_small_amount():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        resp = test_client.post(
            URL,
            json=_payload(order_id="ORD-SMALL", fiat_amount=0.01, token_symbol="USDC", network="ETHEREUM"),
        )
    assert resp.status_code == 201
    assert resp.json()["crypto_amount"] == "0.000285"


def test_unsupported_currency_doge():
    _clear_payments()
    resp = test_client.post(URL, json=_payload(order_id="ORD-DOGE", token_symbol="DOGE"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Unsupported Currency"}


def test_unsupported_fiat_currency():
    resp = test_client.post(URL, json=_payload(order_id="ORD-USD", fiat_currency="USD"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Unsupported Currency"}


def test_unsupported_network():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NET", network="polygon"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Unsupported Network"}


def test_order_id_missing():
    resp = test_client.post(URL, json=_payload(order_id=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Order ID is required"}


def test_order_id_whitespace():
    resp = test_client.post(URL, json=_payload(order_id="   "))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Order ID is required"}


def test_fiat_amount_missing():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NOAMT", fiat_amount=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Fiat amount is required"}


def test_fiat_amount_not_number():
    resp = test_client.post(URL, json=_payload(order_id="ORD-ABC", fiat_amount="abc"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Fiat amount must be a number"}


def test_fiat_amount_zero():
    resp = test_client.post(URL, json=_payload(order_id="ORD-ZERO", fiat_amount=0))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Fiat amount must be greater than zero"}


def test_fiat_amount_negative():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NEG", fiat_amount=-5))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Fiat amount must be greater than zero"}


def test_fiat_currency_missing():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NOCUR", fiat_currency=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Fiat currency is required"}


def test_token_symbol_missing():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NOTOK", token_symbol=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Token symbol is required"}


def test_network_missing():
    resp = test_client.post(URL, json=_payload(order_id="ORD-NONET", network=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Network is required"}


def test_rate_unavailable():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(side_effect=rate_source.RateUnavailable("down"))):
        resp = test_client.post(URL, json=_payload(order_id="ORD-DOWN"))
    assert resp.status_code == 502
    assert resp.json() == {"detail": "Exchange rate unavailable"}


def test_idempotency_same_order():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        first = test_client.post(URL, json=_payload(order_id="ORD-IDEM"))
        second = test_client.post(URL, json=_payload(order_id="ORD-IDEM"))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert first.json()["wallet_address"] == second.json()["wallet_address"]
    assert first.json()["crypto_amount"] == second.json()["crypto_amount"]
    assert _count_rows("ORD-IDEM") == 1


def test_idempotency_after_expiry_creates_new():
    _clear_payments()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        first = test_client.post(URL, json=_payload(order_id="ORD-EXP"))
    db = SessionLocal()
    row = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == "ORD-EXP").first()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    db.close()
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        second = test_client.post(URL, json=_payload(order_id="ORD-EXP"))
    assert second.status_code == 201
    assert first.json()["payment_id"] != second.json()["payment_id"]
    assert _count_rows("ORD-EXP") == 2


def test_sql_injection_order_id_accepted():
    _clear_payments()
    evil = "'; DROP TABLE payment_transactions;--"
    with patch.object(payments_module, "fetch_rate", new=AsyncMock(return_value=35.5)):
        resp = test_client.post(URL, json=_payload(order_id=evil))
    assert resp.status_code == 201
    db = SessionLocal()
    row = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == evil).first()
    assert row is not None
    db.close()