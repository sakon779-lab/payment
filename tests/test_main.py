from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "Pass1!"})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 3
    assert data['strength'] == 'Medium'
    assert 'Password is too short' in data['feedback']

def test_check_password_medium():
    response = client.post("/check-password", json={"password": "Password1"})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 3
    assert data['strength'] == 'Medium'
    assert 'Add a special character' in data['feedback']

def test_check_password_strong():
    response = client.post("/check-password", json={"password": "Password1!"})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 4
    assert data['strength'] == 'Strong'
    assert data['feedback'] == []

def test_check_password_empty():
    response = client.post("/check-password", json={"password": ""})
    assert response.status_code == 400
    data = response.json()
    assert data['detail'] == 'Password cannot be empty'

def test_check_password_missing_field():
    response = client.post("/check-password", json={})
    assert response.status_code == 422

def test_check_password_null_value():
    response = client.post("/check-password", json={"password": None})
    assert response.status_code == 422