from fastapi.testclient import TestClient
import pytest
from src.main import app

client = TestClient(app)

def test_checkout_validation_user_id_missing():
    response = client.post("/api/v1/checkout", json={
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkout_validation_user_id_invalid():
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkout_validation_product_id_missing():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "amount": 1500.00
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkout_validation_product_id_empty():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "",
        "amount": 1500.00
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkout_validation_amount_missing():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01"
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_checkout_validation_amount_invalid():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 0
    })
    
    assert response.status_code == 422
    assert "detail" in response.json()
