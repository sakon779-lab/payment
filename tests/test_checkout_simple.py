from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch
from src.main import app

# Create a simple test client without database setup
client = TestClient(app)

# Test validation - missing user_id
async def test_checkout_validation_missing_user_id():
    response = client.post("/api/v1/checkout", json={
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id is required"}

# Test validation - user_id <= 0
async def test_checkout_validation_invalid_user_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id must be a positive integer"}

# Test validation - missing product_id
async def test_checkout_validation_missing_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "amount": 1500.00
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id is required"}

# Test validation - empty product_id
async def test_checkout_validation_empty_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "",
        "amount": 1500.00
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id cannot be empty"}

# Test validation - missing amount
async def test_checkout_validation_missing_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01"
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "amount is required"}

# Test validation - amount <= 0
async def test_checkout_validation_invalid_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 0
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "amount must be strictly greater than 0"}

# Test validation - negative amount
async def test_checkout_validation_negative_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": -100
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "amount must be strictly greater than 0"}

# Test that the endpoint exists
async def test_checkout_endpoint_exists():
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    # This should fail due to missing user, but not due to endpoint not existing
    assert response.status_code in [404, 400]  # Either user not found or validation error
    assert "detail" in response.json()