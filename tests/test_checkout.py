import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.database import get_db

# Setup Test Client
client = TestClient(app)

# Mock database dependency
mock_db = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db


def test_checkout_valid_request():
    # Mock user exists
    mock_user = MagicMock()
    mock_user.id = 999
    mock_db.execute.return_value.fetchone.return_value = mock_user
    
    # Mock successful payment
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "SUCCESS", "txn_id": "mock_txn_888"}
        mock_post.return_value = mock_response
        
        # Mock successful order creation
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        
        response = client.post("/api/v1/checkout", json={
            "user_id": 999,
            "product_id": "PROD-01",
            "amount": 1500.00
        })
        
        assert response.status_code == 201
        assert response.json() == {"order_status": "COMPLETED"}


def test_checkout_user_not_found():
    # Mock user does not exist
    mock_db.execute.return_value.fetchone.return_value = None
    
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_checkout_payment_declined():
    # Mock user exists
    mock_user = MagicMock()
    mock_user.id = 999
    mock_db.execute.return_value.fetchone.return_value = mock_user
    
    # Mock declined payment
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"status": "DECLINED", "reason": "Insufficient Funds"}
        mock_post.return_value = mock_response
        
        response = client.post("/api/v1/checkout", json={
            "user_id": 999,
            "product_id": "PROD-01",
            "amount": 1500.00
        })
        
        assert response.status_code == 402
        assert response.json() == {"error": "Payment Declined"}


def test_checkout_missing_user_id():
    response = client.post("/api/v1/checkout", json={
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422


def test_checkout_invalid_user_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": -1,
        "product_id": "PROD-01",
        "amount": 1500.00
    })
    
    assert response.status_code == 422


def test_checkout_missing_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "amount": 1500.00
    })
    
    assert response.status_code == 422


def test_checkout_empty_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "",
        "amount": 1500.00
    })
    
    assert response.status_code == 422


def test_checkout_missing_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01"
    })
    
    assert response.status_code == 422


def test_checkout_invalid_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": 999,
        "product_id": "PROD-01",
        "amount": -100.00
    })
    
    assert response.status_code == 422