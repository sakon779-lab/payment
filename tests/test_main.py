from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)

def test_check_password_valid_strong():
    response = test_client.post('/check-password', json={'password': 'A1!abcde'})
    assert response.status_code == 200
    assert response.json() == {'score': 4, 'strength': 'Strong', 'feedbacks': []}

def test_check_password_valid_medium():
    response = test_client.post('/check-password', json={'password': 'A1!abcd'})
    assert response.status_code == 200
    assert response.json() == {'score': 3, 'strength': 'Medium', 'feedbacks': ['Password is too short']}

def test_check_password_valid_weak():
    response = test_client.post('/check-password', json={'password': 'A1!a'})
    assert response.status_code == 200
    assert response.json() == {'score': 3, 'strength': 'Medium', 'feedbacks': ['Password is too short']}

def test_check_password_invalid_empty():
    response = test_client.post('/check-password', json={'password': ''})
    assert response.status_code == 400
    assert response.json() == {'detail': 'Password cannot be empty'}

def test_check_password_missing_field():
    response = test_client.post('/check-password', json={})
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'

def test_check_password_null_value():
    response = test_client.post('/check-password', json={'password': None})
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Input should be a valid string'