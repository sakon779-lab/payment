from fastapi.testclient import TestClient
from src.main import app, SessionLocal, User, Order

client = TestClient(app)

# --- Pure rules_code tests ---
def test_rules_code_bronze_zero():
    from src.main import rules_code
    result = rules_code(0)
    assert result == {"tier": "Bronze", "cashback_percent": 0, "next_tier": "Silver", "spend_to_next_tier": 5000}

def test_rules_code_bronze_4999():
    from src.main import rules_code
    result = rules_code(4999)
    assert result == {"tier": "Bronze", "cashback_percent": 0, "next_tier": "Silver", "spend_to_next_tier": 1}

def test_rules_code_silver_5000():
    from src.main import rules_code
    result = rules_code(5000)
    assert result == {"tier": "Silver", "cashback_percent": 1, "next_tier": "Gold", "spend_to_next_tier": 15000}

def test_rules_code_silver_12500():
    from src.main import rules_code
    result = rules_code(12500)
    assert result == {"tier": "Silver", "cashback_percent": 1, "next_tier": "Gold", "spend_to_next_tier": 7500}

def test_rules_code_gold_20000():
    from src.main import rules_code
    result = rules_code(20000)
    assert result == {"tier": "Gold", "cashback_percent": 2, "next_tier": "Platinum", "spend_to_next_tier": 30000}

def test_rules_code_gold_49999():
    from src.main import rules_code
    result = rules_code(49999)
    assert result == {"tier": "Gold", "cashback_percent": 2, "next_tier": "Platinum", "spend_to_next_tier": 1}

def test_rules_code_platinum_50000():
    from src.main import rules_code
    result = rules_code(50000)
    assert result == {"tier": "Platinum", "cashback_percent": 5, "next_tier": None, "spend_to_next_tier": 0}

# --- Integration tests ---
def test_loyalty_no_orders():
    db = SessionLocal()
    user = User(id=1, status="active")
    db.add(user)
    db.commit()
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

def test_loyalty_completed_4999():
    db = SessionLocal()
    user = User(id=2, status="active")
    db.add(user)
    db.add(Order(user_id=2, product_id="PROD-01", amount=4999, status="COMPLETED"))
    db.commit()
    db.close()
    
    response = client.get("/api/v1/users/2/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 4999
    assert data["tier"] == "Bronze"
    assert data["cashback_percent"] == 0
    assert data["next_tier"] == "Silver"
    assert data["spend_to_next_tier"] == 1

def test_loyalty_completed_5000():
    db = SessionLocal()
    user = User(id=3, status="active")
    db.add(user)
    db.add(Order(user_id=3, product_id="PROD-01", amount=5000, status="COMPLETED"))
    db.commit()
    db.close()
    
    response = client.get("/api/v1/users/3/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 5000
    assert data["tier"] == "Silver"
    assert data["cashback_percent"] == 1
    assert data["next_tier"] == "Gold"
    assert data["spend_to_next_tier"] == 15000

def test_loyalty_completed_30000_cancelled_25000():
    db = SessionLocal()
    user = User(id=4, status="active")
    db.add(user)
    db.add(Order(user_id=4, product_id="PROD-01", amount=30000, status="COMPLETED"))
    db.add(Order(user_id=4, product_id="PROD-02", amount=25000, status="CANCELLED"))
    db.commit()
    db.close()
    
    response = client.get("/api/v1/users/4/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 30000
    assert data["tier"] == "Gold"
    assert data["cashback_percent"] == 2
    assert data["next_tier"] == "Platinum"
    assert data["spend_to_next_tier"] == 20000

def test_loyalty_completed_50000():
    db = SessionLocal()
    user = User(id=5, status="active")
    db.add(user)
    db.add(Order(user_id=5, product_id="PROD-01", amount=50000, status="COMPLETED"))
    db.commit()
    db.close()
    
    response = client.get("/api/v1/users/5/loyalty")
    assert response.status_code == 200
    data = response.json()
    assert data["total_spend"] == 50000
    assert data["tier"] == "Platinum"
    assert data["cashback_percent"] == 5
    assert data["next_tier"] is None
    assert data["spend_to_next_tier"] == 0

def test_loyalty_user_not_found():
    response = client.get("/api/v1/users/999/loyalty")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}