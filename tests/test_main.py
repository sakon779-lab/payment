from fastapi.testclient import TestClient
from src.main import app, PasswordRequest, evaluate_password_strength
test_client = TestClient(app)
def test_check_password_weak():
    response = test_client.post('/check-password', json={'password': 'pass'})
    assert response.status_code == 200
    assert response.json() == {
        'score': 0,
        'strength': 'Weak',
        'feedback': ['Password is too short', 'Add a number', 'Add an uppercase letter', 'Add a special character']
    }
def test_check_password_medium():
    response = test_client.post('/check-password', json={'password': 'Pass1!'})
    assert response.status_code == 200
    assert response.json() == {
        'score': 3,
        'strength': 'Medium',
        'feedback': ['Password is too short']
    }
def test_check_password_strong():
    response = test_client.post('/check-password', json={'password': 'Password123!'})
    assert response.status_code == 200
    assert response.json() == {
        'score': 4,
        'strength': 'Strong',
        'feedback': []
    }
def test_check_password_empty():
    response = test_client.post('/check-password', json={'password': ''})
    assert response.status_code == 400
    assert response.json() == {'detail': ['Password cannot be empty']}
def test_check_password_missing_field():
    response = test_client.post('/check-password', json={})
    assert response.status_code == 422