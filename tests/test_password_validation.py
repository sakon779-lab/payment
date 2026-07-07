import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_password_None_value():
    """Test that None password returns 400 with 'Password is required'"""
    response = client.post("/check-password", json={"password": None})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password is required"}

def test_password_missing_field():
    """Test that missing password field returns 400 with 'Password is required'"""
    response = client.post("/check-password", json={})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password is required"}

def test_password_empty_string():
    """Test that empty password returns 400 with 'Password cannot be empty'"""
    response = client.post("/check-password", json={"password": ""})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}

def test_password_whitespace_only():
    """Test that whitespace-only password returns 400 with 'Password cannot be empty'"""
    response = client.post("/check-password", json={"password": "   "})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}

def test_password_valid():
    """Test that valid password returns 200 with correct response"""
    response = client.post("/check-password", json={"password": "StrongP@ss1"})
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "strength" in data
    assert "feedback" in data
