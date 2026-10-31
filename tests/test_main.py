from fastapi.testclient import TestClient
import pytest
from src.main import app

client = TestClient(app)

def test_check_password_empty():
    # src/main.py's RequestValidationError handler (6a197f7) replaces FastAPI's
    # default 422 envelope with a flat 400 + {"detail": ...}. Status and message
    # are SCRUM-29's error contract, asserted verbatim the same way
    # qa-automation-repo/tests/payment_service/SCRUM-29.robot asserts them.
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