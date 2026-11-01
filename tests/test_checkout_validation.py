"""Checkout request validation — the status and the message both come from spec.

src/main.py's RequestValidationError handler (6a197f7, 3 Mar 2026) answers every
validation failure with **400** and a flat ``{"detail": "<message>"}`` body, not
FastAPI's default 422 envelope. These tests were written before that handler and
kept asserting 422, so they have been red ever since.

Each expectation below is the same row that
``qa-automation-repo/tests/payment_service/SCRUM-30.robot`` asserts — status and
``detail`` verbatim. The old tests only checked that *some* ``detail`` key
existed, which passes for any error at all; that is why eight months of drift
went unnoticed. Assert the message, not the presence of a message.
"""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def assert_rejected(body, expected_detail):
    response = client.post("/api/v1/checkout", json=body)
    assert response.status_code == 400
    assert response.json() == {"detail": expected_detail}


def test_checkout_validation_user_id_missing():
    assert_rejected(
        {"product_id": "PROD-01", "amount": 1500.00},
        "user_id is required",
    )


def test_checkout_validation_user_id_invalid():
    assert_rejected(
        {"user_id": 0, "product_id": "PROD-01", "amount": 1500.00},
        "user_id must be a positive integer",
    )


def test_checkout_validation_product_id_missing():
    assert_rejected(
        {"user_id": 1, "amount": 1500.00},
        "product_id is required",
    )


def test_checkout_validation_product_id_empty():
    assert_rejected(
        {"user_id": 1, "product_id": "", "amount": 1500.00},
        "product_id cannot be empty",
    )


def test_checkout_validation_amount_missing():
    assert_rejected(
        {"user_id": 1, "product_id": "PROD-01"},
        "amount is required",
    )


def test_checkout_validation_amount_invalid():
    assert_rejected(
        {"user_id": 1, "product_id": "PROD-01", "amount": 0},
        "amount must be strictly greater than 0",
    )
