from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch
from src.main import app, Base, engine
from sqlalchemy.orm import sessionmaker

# Setup test database
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

# Test data
TEST_USER_ID = 999
TEST_PRODUCT_ID = "PROD-01"
TEST_AMOUNT = 1500.00

@pytest.fixture(scope="function")
async def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Setup test data
    db = TestingSessionLocal()
    try:
        # Insert a test user
        from src.main import User
        user = User(id=TEST_USER_ID, status="ACTIVE")
        db.add(user)
        db.commit()
        yield db
    finally:
        db.close()
        # Clean up
        Base.metadata.drop_all(bind=engine)


def test_checkout_success():
    # Setup
    with patch('src.main.httpx.AsyncClient') as mock_client:
        # Mock successful payment response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "SUCCESS", "txn_id": "mock_txn_888"}
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        
        # Test
        response = client.post("/api/v1/checkout", json={
            "user_id": TEST_USER_ID,
            "product_id": TEST_PRODUCT_ID,
            "amount": TEST_AMOUNT
        })
        
        # Assert
        assert response.status_code == 201
        assert response.json() == {"order_status": "COMPLETED"}


def test_checkout_payment_declined():
    # Setup
    with patch('src.main.httpx.AsyncClient') as mock_client:
        # Mock declined payment response
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"status": "DECLINED", "reason": "Insufficient Funds"}
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        
        # Test
        response = client.post("/api/v1/checkout", json={
            "user_id": TEST_USER_ID,
            "product_id": TEST_PRODUCT_ID,
            "amount": TEST_AMOUNT
        })
        
        # Assert
        assert response.status_code == 402
        assert response.json() == {"detail": "Payment Declined"}


def test_checkout_user_not_found():
    # Test with non-existent user
    response = client.post("/api/v1/checkout", json={
        "user_id": 9999,  # Non-existent user
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_checkout_missing_user_id():
    response = client.post("/api/v1/checkout", json={
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


def test_checkout_invalid_user_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": 0,
        "product_id": TEST_PRODUCT_ID,
        "amount": TEST_AMOUNT
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


def test_checkout_missing_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "amount": TEST_AMOUNT
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


def test_checkout_empty_product_id():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": "",
        "amount": TEST_AMOUNT
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


def test_checkout_missing_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error


def test_checkout_invalid_amount():
    response = client.post("/api/v1/checkout", json={
        "user_id": TEST_USER_ID,
        "product_id": TEST_PRODUCT_ID,
        "amount": 0
    })
    
    # Assert
    assert response.status_code == 422  # Pydantic validation error
