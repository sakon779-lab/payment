from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)

def test_hello_endpoint():
    response = test_client.get('/hello/World')
    assert response.status_code == 200
    assert response.json() == {'message': 'Hello, World!'}

from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)

def test_check_password_empty():
    response = test_client.post('/check-password', json={})
    assert response.status_code == 422
    assert 'detail' in response.json()
