from fastapi.testclient import TestClient
import pytest
from src.main import app

client = TestClient(app)

def test_check_password_empty():
    response = client.post("/check-password", json={"password": ""})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "abc"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 0,
        "strength": "Weak",
        "feedback": ["Password is too short", "Add a number", "Add an uppercase letter", "Add a special character"]
    }

def test_check_password_medium():
    response = client.post("/check-password", json={"password": "Ab1"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 2,
        "strength": "Medium",
        "feedback": ["Password is too short", "Add a special character"]
    }

def test_check_password_strong():
    response = client.post("/check-password", json={"password": "StrongP@ss1"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 4,
        "strength": "Strong",
        "feedback": []
    }