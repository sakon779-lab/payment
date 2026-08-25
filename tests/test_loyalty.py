"""Tests for SCRUM-37: Customer Loyalty Status API."""
from fastapi.testclient import TestClient
from src.main import app, SessionLocal, User, Order

test_client = TestClient(app)


def seed_user(user_id, status="active"):
    db = SessionLocal()
    user = User(id=user_id, status=status)
    db.add(user)
    db.commit()
    db.close()


def seed_order(user_id, amount, status):
    db = SessionLocal()
    order = Order(user_id=user_id, product_id="P1", amount=amount, status=status)
    db.add(order)
    db.commit()
    db.close()


def test_loyalty_user_not_found():
    """user_id not in DB -> 404 {"detail": "User not found"}"""
    response = test_client.get("/api/v1/users/999/loyalty")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_loyalty_negative_user_id():
    """user_id 0 or negative -> no such row in users -> 404"""
    response = test_client.get("/api/v1/users/-1/loyalty")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_loyalty_no_orders_bronze():
    """user with no orders -> total_spend 0 -> Bronze"""
    seed_user(1)
    response = test_client.get("/api/v1/users/1/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["total_spend"] == 0
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 5000


def test_loyalty_completed_4999_bronze():
    """user with COMPLETED 4,999 -> total_spend 4999 -> Bronze"""
    seed_user(2)
    seed_order(2, 4999, "COMPLETED")
    response = test_client.get("/api/v1/users/2/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 4999
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 1


def test_loyalty_completed_5000_silver():
    """user with COMPLETED 5,000 -> total_spend 5000 -> Silver"""
    seed_user(3)
    seed_order(3, 5000, "COMPLETED")
    response = test_client.get("/api/v1/users/3/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 5000
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 15000


def test_loyalty_completed_12500_silver():
    """user with COMPLETED 12,500 -> total_spend 12500 -> Silver"""
    seed_user(4)
    seed_order(4, 12500, "COMPLETED")
    response = test_client.get("/api/v1/users/4/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 12500
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 7500


def test_loyalty_completed_20000_gold():
    """user with COMPLETED 20,000 -> total_spend 20000 -> Gold"""
    seed_user(5)
    seed_order(5, 20000, "COMPLETED")
    response = test_client.get("/api/v1/users/5/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 20000
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 30000


def test_loyalty_completed_49999_gold():
    """user with COMPLETED 49,999 -> total_spend 49999 -> Gold"""
    seed_user(6)
    seed_order(6, 49999, "COMPLETED")
    response = test_client.get("/api/v1/users/6/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 49999
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 1


def test_loyalty_completed_50000_platinum():
    """user with COMPLETED 50,000 -> total_spend 50000 -> Platinum"""
    seed_user(7)
    seed_order(7, 50000, "COMPLETED")
    response = test_client.get("/api/v1/users/7/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 50000
    assert data["tier"] == "Platinum"
    assert data["cashback_percent"] == 5
    assert data["next_tier"] is None
    assert data["spend_to_next_tier"] == 0


def test_loyalty_excludes_cancelled():
    """user with COMPLETED 30,000 + CANCELLED 25,000 -> total_spend 30000 -> Gold"""
    seed_user(8)
    seed_order(8, 30000, "COMPLETED")
    seed_order(8, 25000, "CANCELLED")
    response = test_client.get("/api/v1/users/8/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 30000
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 20000


def test_loyalty_excludes_pending():
    """PENDING orders are excluded exactly like CANCELLED ones"""
    seed_user(9)
    seed_order(9, 5000, "COMPLETED")
    seed_order(9, 100000, "PENDING")
    response = test_client.get("/api/v1/users/9/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 5000
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 15000