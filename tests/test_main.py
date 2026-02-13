from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_check_password_weak():
    response = client.post('/check-password', json={"password": "123"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 1,
        "strength": "Weak",
        "feedback": ["Password is too short", "Add an uppercase letter", "Add a special character"]
    }

def test_check_password_medium():
    response = client.post('/check-password', json={"password": "Ab1"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 2,
        "strength": "Medium",
        "feedback": ["Password is too short", "Add a special character"]
    }

def test_check_password_strong():
    response = client.post('/check-password', json={"password": "StrongP@ss1"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 4,
        "strength": "Strong",
        "feedback": []
    }

def test_check_password_empty():
    response = client.post('/check-password', json={"password": ""})
    assert response.status_code == 422
    # Pydantic validation error response structure

def test_check_password_whitespace():
    response = client.post('/check-password', json={"password": "   "})
    assert response.status_code == 422
    # Pydantic validation error response structure

def test_check_password_missing_field():
    response = client.post('/check-password', json={})
    assert response.status_code == 422
    # Pydantic validation error response structure