from fastapi.testclient import TestClient
from src.main import app, Base, engine, SessionLocal, User, Order

client = TestClient(app)

def seed_user(db, user_id=1):
    user = User(id=user_id, status="ACTIVE")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def seed_order(db, user_id, amount, status):
    order = Order(user_id=user_id, product_id="PROD-01", amount=amount, status=status)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def test_loyalty_user_not_found():
    response = client.get("/api/v1/users/999/loyalty")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_loyalty_no_orders_bronze():
    db = SessionLocal()
    seed_user(db, user_id=1)
    db.close()
    
    response = client.get("/api/v1/users/1/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["total_spend"] == 0
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 5000

def test_loyalty_completed_4999_bronze():
    db = SessionLocal()
    seed_user(db, user_id=2)
    seed_order(db, user_id=2, amount=4999, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/2/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 4999
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 1

def test_loyalty_completed_5000_silver():
    db = SessionLocal()
    seed_user(db, user_id=3)
    seed_order(db, user_id=3, amount=5000, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/3/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 5000
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 15000

def test_loyalty_completed_12500_silver():
    db = SessionLocal()
    seed_user(db, user_id=4)
    seed_order(db, user_id=4, amount=12500, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/4/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 12500
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 7500

def test_loyalty_completed_20000_gold():
    db = SessionLocal()
    seed_user(db, user_id=5)
    seed_order(db, user_id=5, amount=20000, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/5/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 20000
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 30000

def test_loyalty_completed_49999_gold():
    db = SessionLocal()
    seed_user(db, user_id=6)
    seed_order(db, user_id=6, amount=49999, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/6/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 49999
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 1

def test_loyalty_completed_50000_platinum():
    db = SessionLocal()
    seed_user(db, user_id=7)
    seed_order(db, user_id=7, amount=50000, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/7/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 50000
    assert data["tier"] == "Platinum"
    assert data["cashback_percent"] == 5
    assert data["next_tier"] is None
    assert data["spend_to_next_tier"] == 0

def test_loyalty_cancelled_excluded():
    db = SessionLocal()
    seed_user(db, user_id=8)
    seed_order(db, user_id=8, amount=30000, status="COMPLETED")
    seed_order(db, user_id=8, amount=25000, status="CANCELLED")
    db.close()
    
    response = client.get("/api/v1/users/8/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 30000
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 20000

def test_loyalty_pending_excluded():
    db = SessionLocal()
    seed_user(db, user_id=9)
    seed_order(db, user_id=9, amount=10000, status="PENDING")
    db.close()
    
    response = client.get("/api/v1/users/9/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 0
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 5000

def test_loyalty_multiple_completed_sum():
    db = SessionLocal()
    seed_user(db, user_id=10)
    seed_order(db, user_id=10, amount=8000, status="COMPLETED")
    seed_order(db, user_id=10, amount=4500, status="COMPLETED")
    db.close()
    
    response = client.get("/api/v1/users/10/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 12500
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 7500