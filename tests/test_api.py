from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)

# Existing tests

def test_hello_endpoint():
    response = test_client.get('/hello/World')
    assert response.status_code == 200
    assert response.json() == {'message': 'Hello, World!'}

def test_reverse_string():
    response = test_client.get('/reverse/hello')
    assert response.status_code == 200
    assert response.json() == {'original': 'hello', 'reversed': 'olleh'}

# New test for password strength checker

def test_check_password_strength():
    payload = {
        "password": "Password123!"
    }
    response = test_client.post('/check-password', json=payload)
    assert response.status_code == 200
    expected_response = {
        'strength': 'Strong',
        'score': 4,
        'feedback': []
    }
    assert response.json() == expected_response