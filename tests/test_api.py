

from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)



def test_reverse_endpoint():
    response = test_client.get('/reverse/hello')
    assert response.status_code == 200
    assert response.json() == {'original': 'hello', 'reversed': 'olleh'}
