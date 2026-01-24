from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)

def test_hello_endpoint():
    response = test_client.get('/hello/World')
    assert response.status_code == 200
    assert response.json() == {'message': 'Hello, World!'}