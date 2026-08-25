from sqlalchemy.orm import sessionmaker
from src.main import app, Base, engine, User, Order, get_db
from src.routers.loyalty import get_loyalty

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_user(user_id):
    db = TestingSessionLocal()
    user = User(id=user_id, status="active")
    db.add(user)
    db.commit()
    db.close()

def seed_order(user_id, amount, status):
    db = TestingSessionLocal()
    order = Order(user_id=user_id, product_id="PROD-01", amount=amount, status=status)
    db.add(order)
    db.commit()
    db.close()

def test_loyalty_no_orders():
    seed_user(1)
    db = TestingSessionLocal()
    result = get_loyalty(1, db)
    db.close()
    assert result["user_id"] == 1
    assert result["total_spend"] == 0
    assert result["tier"] == "Bronze"
    assert result["cashback_percent"] == 0
    assert result["next_tier"] == "Silver"
    assert result["spend_to_next_tier"] == 5000

def test_loyalty_bronze_4999():
    seed_user(2)
    seed_order(2, 4999, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(2, db)
    db.close()
    assert result["total_spend"] == 4999
    assert result["tier"] == "Bronze"
    assert result["cashback_percent"] == 0
    assert result["next_tier"] == "Silver"
    assert result["spend_to_next_tier"] == 1

def test_loyalty_silver_5000():
    seed_user(3)
    seed_order(3, 5000, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(3, db)
    db.close()
    assert result["total_spend"] == 5000
    assert result["tier"] == "Silver"
    assert result["cashback_percent"] == 1
    assert result["next_tier"] == "Gold"
    assert result["spend_to_next_tier"] == 15000

def test_loyalty_silver_12500():
    seed_user(4)
    seed_order(4, 12500, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(4, db)
    db.close()
    assert result["total_spend"] == 12500
    assert result["tier"] == "Silver"
    assert result["cashback_percent"] == 1
    assert result["next_tier"] == "Gold"
    assert result["spend_to_next_tier"] == 7500

def test_loyalty_gold_20000():
    seed_user(5)
    seed_order(5, 20000, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(5, db)
    db.close()
    assert result["total_spend"] == 20000
    assert result["tier"] == "Gold"
    assert result["cashback_percent"] == 2
    assert result["next_tier"] == "Platinum"
    assert result["spend_to_next_tier"] == 30000

def test_loyalty_gold_49999():
    seed_user(6)
    seed_order(6, 49999, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(6, db)
    db.close()
    assert result["total_spend"] == 49999
    assert result["tier"] == "Gold"
    assert result["cashback_percent"] == 2
    assert result["next_tier"] == "Platinum"
    assert result["spend_to_next_tier"] == 1

def test_loyalty_platinum_50000():
    seed_user(7)
    seed_order(7, 50000, "COMPLETED")
    db = TestingSessionLocal()
    result = get_loyalty(7, db)
    db.close()
    assert result["total_spend"] == 50000
    assert result["tier"] == "Platinum"
    assert result["cashback_percent"] == 5
    assert result["next_tier"] is None
    assert result["spend_to_next_tier"] == 0

def test_loyalty_excludes_cancelled():
    seed_user(8)
    seed_order(8, 30000, "COMPLETED")
    seed_order(8, 25000, "CANCELLED")
    db = TestingSessionLocal()
    result = get_loyalty(8, db)
    db.close()
    assert result["total_spend"] == 30000
    assert result["tier"] == "Gold"
    assert result["cashback_percent"] == 2
    assert result["next_tier"] == "Platinum"
    assert result["spend_to_next_tier"] == 20000

def test_loyalty_excludes_pending():
    seed_user(9)
    seed_order(9, 5000, "COMPLETED")
    seed_order(9, 10000, "PENDING")
    db = TestingSessionLocal()
    result = get_loyalty(9, db)
    db.close()
    assert result["total_spend"] == 5000
    assert result["tier"] == "Silver"
    assert result["cashback_percent"] == 1

def test_loyalty_user_not_found():
    db = TestingSessionLocal()
    try:
        get_loyalty(999, db)
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert e.status_code == 404
        assert e.detail == "User not found"
    finally:
        db.close()

def test_loyalty_user_id_zero():
    db = TestingSessionLocal()
    try:
        get_loyalty(0, db)
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert e.status_code == 404
        assert e.detail == "User not found"
    finally:
        db.close()