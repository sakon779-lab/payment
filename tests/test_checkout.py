from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import Base, get_db, app, User, Order

# Setup in-memory database for tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Test cases for checkout endpoint
def test_checkout_success():
    # Setup test user
    db = TestingSessionLocal()
    user = User(id=999, status="ACTIVE")
    db.add(user)
    db.commit()
    db.close()

    # Mock external payment gateway
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(status_code=200)
        mock_post.return_value.json = AsyncMock(return_value={"status": "SUCCESS", "txn_id": "mock_txn_888"})
        
        response = client.post("/api/v1/checkout", json={
            "user_id": 999,
            "product_id": "PROD-01",
            "amount": 1500.00
        })
        
        assert response.status_code == 201
        assert response.json() == {"order_status": "COMPLETED"}

def test_checkout_payment_declined():
    # Setup test user
    db = TestingSessionLocal()
    user = User(id=999, status="ACTIVE")
    db.add(user)
    db.commit()
    db.close()

    # Mock external payment gateway
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(status_code=400)
        mock_post.return_value.json = AsyncMock(return_value={"status": "DECLINED", "reason": "Insufficient Funds"})
        
        response = client.post("/api/v1/checkout", json={
            "user_id": 999,
            "product_id": "PROD-01",
            "amount": 1500.00
        })
        
        assert response.status_code == 402
        assert response.json() == {"detail": "Payment Declined"}

def test_checkout_user_not_found():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_checkout_validation_user_id_missing():
    response = client.post("/api/v1/checkout", json={
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422

def test_checkout_validation_user_id_invalid():
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422

def test_checkout_validation_product_id_missing():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "amount": 1500.00
    })
    
    assert response.status_code == 422

def test_checkout_validation_product_id_empty():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "",
        "amount": 1500.00
    })
    
    assert response.status_code == 422

def test_checkout_validation_amount_missing():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01"
    })
    
    assert response.status_code == 422

def test_checkout_validation_amount_invalid():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01",
        "amount": 0
    })
    
    assert response.status_code == 422