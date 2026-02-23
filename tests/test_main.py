from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_greet():
    response = client.get('/hello/Olympus')
    assert response.status_code == 200
    assert response.json() == {'message': 'Hello, Olympus!'}

def test_reverse_string():
    response = client.get('/reverse/Python')
    assert response.status_code == 200
    assert response.json() == {'original': 'Python', 'reversed': 'nohtyP'}

def test_check_password_success():
    response = client.post('/check-password', json={"password": "StrongPass1!"})
    assert response.status_code == 200
    assert response.json() == {"score": 4, "strength": "Strong", "feedback": []}

def test_check_password_failure():
    response = client.post('/check-password', json={"password": "weak"})
    assert response.status_code == 200
    assert response.json()['score'] == 0
    assert response.json()['strength'] == "Weak"
    assert response.json()['feedback'] == ["Password is too short", "Add a number", "Add an uppercase letter", "Add a special character"]

def test_process_payment_success():
    response = client.post('/process_payment', json={"amount": 100.0, "currency": "USD", "payment_method": "credit_card"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Payment processed successfully"}

def test_process_payment_failure():
    response = client.post('/process_payment', json={"amount": -10.0, "currency": "USD", "payment_method": "credit_card"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Payment processing failed: Amount must be positive"}