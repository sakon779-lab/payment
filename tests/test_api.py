from fastapi.testclient import TestClient
from src.main import app
test_client = TestClient(app)

def test_check_password():
    response = test_client.post('/check-password', json={'password': 'Test123!'})
    assert response.status_code == 200
    assert response.json() == {
        'score': 4,
        'feedback': [],
        'strength': 'Strong'
    }