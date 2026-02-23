from fastapi.testclient import TestClient
import pytest
from src.main import app

client = TestClient(app)

def test_calculate_discount_regular():
    response = client.post("/calculate_discount", json={"total_amount": 150.0, "customer_type": "regular"})
    assert response.status_code == 200
    assert response.json() == {"discounted_price": 150.0}

def test_calculate_discount_member():
    response = client.post("/calculate_discount", json={"total_amount": 150.0, "customer_type": "member"})
    assert response.status_code == 200
    assert response.json() == {"discounted_price": 135.0}  # 10% discount

def test_calculate_discount_vip():
    response = client.post("/calculate_discount", json={"total_amount": 150.0, "customer_type": "vip"})
    assert response.status_code == 200
    assert response.json() == {"discounted_price": 120.0}  # 20% discount

def test_calculate_discount_invalid_customer_type():
    response = client.post("/calculate_discount", json={"total_amount": 150.0, "customer_type": "invalid"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid customer type"}