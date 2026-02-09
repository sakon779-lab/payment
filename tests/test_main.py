from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)

# Existing tests...

def test_check_password_empty():
    response = test_client.post('/check-password', json={})
    assert response.status_code == 422
    
def test_check_password_null():
    response = test_client.post('/check-password', json={'password': None})
    assert response.status_code == 422
    
def test_check_password_strength_weak():
    response = test_client.post('/check-password', json={'password': 'weak'})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 0
    assert data['strength'] == 'Weak'
    assert 'Password is too short' in data['feedback']
    
def test_check_password_strength_medium():
    response = test_client.post('/check-password', json={'password': 'Medium1!a'})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 4
    assert data['strength'] == 'Strong'
    
def test_check_password_strength_strong():
    response = test_client.post('/check-password', json={'password': 'Strong1!A'})
    assert response.status_code == 200
    data = response.json()
    assert data['score'] == 4
    assert data['strength'] == 'Strong'
