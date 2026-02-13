from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "abc"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 0,
        "strength": "Weak",
        "feedback": ["Password is too short", "Add a number", "Add an uppercase letter", "Add a special character"]
    }