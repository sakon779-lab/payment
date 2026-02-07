
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_check_password_empty():
    response = client.post('/check-password', json={"password": ""})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}

def test_check_password_missing_field():
    response = client.post('/check-password', json={})
    assert response.status_code == 422

def test_check_password_null_value():
    response = client.post('/check-password', json={"password": None})
    assert response.status_code == 422
