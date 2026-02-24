from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.models import Base, User, Order
from src.database import get_db

# Setup in-memory database
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

class MockAsyncClient:
    def __init__(self):
        self.post_called = False
        self.post_args = None
        self.post_kwargs = None
        
    async def post(self, url, json=None):
        self.post_called = True
        self.post_args = url
        self.post_kwargs = json
        
        # Mock successful payment
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                self.json_data = {"status": "SUCCESS", "txn_id": "mock_txn_888"}
            
            async def json(self):
                return self.json_data
        
        return MockResponse()

# Test successful checkout

def test_checkout_success():
    # Setup test data
    db = TestingSessionLocal()
    user = User(id=1, status='ACTIVE')
    db.add(user)
    db.commit()
    
    client = TestClient(app)
    
    # Mock the httpx.AsyncClient
    from unittest.mock import AsyncMock, patch
    
    with patch('httpx.AsyncClient', return_value=MockAsyncClient()):
        response = client.post('/api/v1/checkout', json={
            'user_id': 1,
            'product_id': 'PROD-01',
            'amount': 1500.00
        })
        
        assert response.status_code == 201
        assert response.json() == {'order_status': 'COMPLETED'}
        
        # Verify order was created
        order = db.query(Order).filter(Order.user_id == 1).first()
        assert order is not None
        assert order.product_id == 'PROD-01'
        assert order.amount == 1500.00
        assert order.status == 'COMPLETED'

# Test payment declined

def test_checkout_payment_declined():
    # Setup test data
    db = TestingSessionLocal()
    user = User(id=1, status='ACTIVE')
    db.add(user)
    db.commit()
    
    client = TestClient(app)
    
    # Mock the httpx.AsyncClient to return 400
    class MockDeclinedResponse:
        def __init__(self):
            self.status_code = 400
            self.json_data = {"status": "DECLINED", "reason": "Insufficient Funds"}
        
        async def json(self):
            return self.json_data
    
    from unittest.mock import patch
    
    with patch('httpx.AsyncClient') as mock_async_client:
        mock_async_client.return_value.post = AsyncMock(return_value=MockDeclinedResponse())
        response = client.post('/api/v1/checkout', json={
            'user_id': 1,
            'product_id': 'PROD-01',
            'amount': 1500.00
        })
        
        assert response.status_code == 402
        assert response.json() == {'detail': 'Payment Declined'}

# Test user not found

def test_checkout_user_not_found():
    client = TestClient(app)
    
    response = client.post('/api/v1/checkout', json={
        'user_id': 999,
        'product_id': 'PROD-01',
        'amount': 1500.00
    })
    
    assert response.status_code == 404
    assert response.json() == {'detail': 'User not found'}

# Test validation errors

def test_checkout_validation_errors():
    client = TestClient(app)
    
    # Test missing user_id
    response = client.post('/api/v1/checkout', json={
        'product_id': 'PROD-01',
        'amount': 1500.00
    })
    assert response.status_code == 422
    
    # Test invalid user_id
    response = client.post('/api/v1/checkout', json={
        'user_id': 0,
        'product_id': 'PROD-01',
        'amount': 1500.00
    })
    assert response.status_code == 400
    assert response.json() == {'detail': 'user_id must be a positive integer'}
    
    # Test missing product_id
    response = client.post('/api/v1/checkout', json={
        'user_id': 1,
        'amount': 1500.00
    })
    assert response.status_code == 422
    
    # Test empty product_id
    response = client.post('/api/v1/checkout', json={
        'user_id': 1,
        'product_id': '',
        'amount': 1500.00
    })
    assert response.status_code == 400
    assert response.json() == {'detail': 'product_id cannot be empty'}
    
    # Test missing amount
    response = client.post('/api/v1/checkout', json={
        'user_id': 1,
        'product_id': 'PROD-01'
    })
    assert response.status_code == 422
    
    # Test invalid amount
    response = client.post('/api/v1/checkout', json={
        'user_id': 1,
        'product_id': 'PROD-01',
        'amount': 0
    })
    assert response.status_code == 400
    assert response.json() == {'detail': 'amount must be strictly greater than 0'}