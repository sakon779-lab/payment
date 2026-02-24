from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.main import app

# Create a mock database session
mock_db = MagicMock()

# Override the get_db dependency
def override_get_db():
    return mock_db

app.dependency_overrides[app.dependency_overrides.get('get_db', lambda: None)] = override_get_db

client = TestClient(app)

# Test successful checkout
@patch('httpx.AsyncClient.post')
async def test_checkout_success(mock_post):
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "SUCCESS", "txn_id": "mock_txn_888"}
    mock_post.return_value = mock_response
    
    # Mock database query to return a user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.status = "ACTIVE"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Mock database add and commit
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()
    
    # Test checkout
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 201
    assert response.json() == {"order_status": "COMPLETED"}
    
    # Verify database operations were called
    mock_db.query.assert_called()
    mock_db.add.assert_called()
    mock_db.commit.assert_called()

# Test payment declined
@patch('httpx.AsyncClient.post')
async def test_checkout_payment_declined(mock_post):
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"status": "DECLINED", "reason": "Insufficient Funds"}
    mock_post.return_value = mock_response
    
    # Mock database query to return a user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.status = "ACTIVE"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Test checkout
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 402
    assert response.json() == {"error": "Payment Declined"}

# Test user not found
async def test_checkout_user_not_found():
    # Mock database query to return None (user not found)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

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

# Test payment gateway error
@patch('httpx.AsyncClient.post')
async def test_checkout_payment_gateway_error(mock_post):
    # Setup mock to raise an exception
    mock_post.side_effect = Exception("Payment gateway timeout")
    
    # Mock database query to return a user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.status = "ACTIVE"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Test checkout
    response = client.post("/api/v1/checkout", json={
        "user_id": 1,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 402
    assert response.json() == {"detail": "Payment Declined"}