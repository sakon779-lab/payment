from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "123"})
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 1
    assert data["strength"] == "Weak"
    assert len(data["feedback"]) == 3

def test_check_password_medium():
    response = client.post("/check-password", json={"password": "Password1"})
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 3
    assert data["strength"] == "Medium"
    assert len(data["feedback"]) == 1

def test_check_password_strong():
    response = client.post("/check-password", json={"password": "P@ssw0rd1"})
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 4
    assert data["strength"] == "Strong"
    assert len(data["feedback"]) == 0

def test_check_password_empty():
    response = client.post("/check-password", json={"password": ""})
    assert response.status_code == 422
    # Pydantic validation error will handle this case with a default message

def test_check_password_whitespace():
    response = client.post("/check-password", json={"password": "   "})
    assert response.status_code == 422
    # Pydantic validation error will handle this case with a default message

def test_check_password_missing_field():
    response = client.post("/check-password", json={})
    assert response.status_code == 422
    # Pydantic validation error will handle this case with a default message