from fastapi.testclient import TestClient
import pytest
from src.main import app
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import Base, User, Order

# Setup test database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[app.dependency_overrides.get('get_db', lambda: None)] = override_get_db

client = TestClient(app)

# Test data
TEST_USER_ID = 999
TEST_PRODUCT_ID = "PROD-01"
TEST_AMOUNT = 1500.00

def test_checkout_missing_user():
    """Test checkout with non-existent user"""
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_checkout_missing_user_id():
    """Test checkout with missing user_id"""
    response = client.post("/api/v1/checkout", json={
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id is required"}

def test_checkout_invalid_user_id():
    """Test checkout with invalid user_id (zero)"""
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id must be a positive integer"}

def test_checkout_missing_product_id():
    """Test checkout with missing product_id"""
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "amount": TEST_AMOUNT
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id is required"}

def test_checkout_empty_product_id():
    """Test checkout with empty product_id"""
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": "",
        "amount": TEST_AMOUNT
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id cannot be empty"}

def test_checkout_missing_amount():
    """Test checkout with missing amount"""
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "amount is required"}

def test_checkout_invalid_amount():
    """Test checkout with invalid amount (zero)"""
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": 0
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "amount must be strictly greater than 0"}

@patch('src.main.httpx.AsyncClient')
def test_checkout_successful(mock_async_client):
    """Test successful checkout"""
    # Setup mock user
    db = TestingSessionLocal()
    user = User(id=TEST_USER_ID, status="ACTIVE")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Setup mock payment response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "SUCCESS", "txn_id": "mock_txn_888"}
    mock_async_client.return_value.post = AsyncMock(return_value=mock_response)
    
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 201
    assert response.json() == {"order_status": "COMPLETED"}
    
    # Verify order was created
    orders = db.query(Order).filter(Order.user_id == TEST_USER_ID).all()
    assert len(orders) == 1
    assert orders[0].product_id == TEST_PRODUCT_ID
    assert orders[0].amount == TEST_AMOUNT
    assert orders[0].status == "COMPLETED"

@patch('src.main.httpx.AsyncClient')
def test_checkout_payment_declined(mock_async_client):
    """Test checkout with declined payment"""
    # Setup mock user
    db = TestingSessionLocal()
    user = User(id=TEST_USER_ID, status="ACTIVE")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Setup mock payment response (declined)
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"status": "DECLINED", "reason": "Insufficient Funds"}
    mock_async_client.return_value.post = AsyncMock(return_value=mock_response)
    
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 402
    assert response.json() == {"detail": "Payment Declined"}

@patch('src.main.httpx.AsyncClient')
def test_checkout_payment_gateway_unavailable(mock_async_client):
    """Test checkout when payment gateway is unavailable"""
    # Setup mock user
    db = TestingSessionLocal()
    user = User(id=TEST_USER_ID, status="ACTIVE")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Setup mock to raise exception
    mock_async_client.return_value.post = AsyncMock(side_effect=Exception("Connection failed"))
    
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Payment gateway is not available"}