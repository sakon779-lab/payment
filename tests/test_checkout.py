from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import Base, get_db, app

# Setup in-memory database for tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Override database dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Test data
TEST_USER_ID = 999
TEST_PRODUCT_ID = "PROD-01"
TEST_AMOUNT = 1500.00

# Test successful checkout
@patch('httpx.AsyncClient.post')
def test_checkout_success(mock_post):
    # Setup mock response
    mock_post.return_value = AsyncMock(status_code=200)
    mock_post.return_value.json = AsyncMock(return_value={"status": "SUCCESS", "txn_id": "mock_txn_888"})
    
    # Create a user in the test database
    response = client.post("/users", json={"id": TEST_USER_ID, "status": "ACTIVE"})
    assert response.status_code == 201
    
    # Test checkout
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 201
    assert response.json() == {"order_status": "COMPLETED"}

# Test payment declined
@patch('httpx.AsyncClient.post')
def test_checkout_payment_declined(mock_post):
    # Setup mock response
    mock_post.return_value = AsyncMock(status_code=400)
    mock_post.return_value.json = AsyncMock(return_value={"status": "DECLINED", "reason": "Insufficient Funds"})
    
    # Create a user in the test database
    response = client.post("/users", json={"id": TEST_USER_ID, "status": "ACTIVE"})
    assert response.status_code == 201
    
    # Test checkout
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 402
    assert response.json() == {"error": "Payment Declined"}

# Test user not found
def test_checkout_user_not_found():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999999,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

# Test validation errors

def test_checkout_missing_user_id():
    response = client.post("/api/v1/checkout", json={
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id is required"}

def test_checkout_invalid_user_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "user_id must be a positive integer"}


def test_checkout_missing_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id is required"}


def test_checkout_empty_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": "",
        "amount": TEST_AMOUNT
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "product_id cannot be empty"}


def test_checkout_missing_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "amount is required"}


def test_checkout_invalid_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": 0
    })
    
    assert response.status_code == 400
    assert response.json() == {"detail": "amount must be strictly greater than 0"}
