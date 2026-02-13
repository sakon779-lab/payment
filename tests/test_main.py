from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_greet():
    response = client.get("/hello/John")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, John!"}

def test_greet_invalid_name():
    response = client.get("/hello/John123")
    assert response.status_code == 400
    assert response.json() == {"detail": "Name must contain only alphabets"}

def test_reverse_string():
    response = client.get("/reverse/HelloWorld")
    assert response.status_code == 200
    assert response.json() == {"original": "HelloWorld", "reversed": "dlroWolleH"}

def test_reverse_string_empty_text():
    response = client.get("/reverse/")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_check_password_weak():
    response = client.post("/check-password", json={"password": "abc"})
    assert response.status_code == 200
    assert response.json() == {
        "score": 0,
        "strength": "Weak",
        "feedback": ["Password is too short", "Add a number", "Add an uppercase letter", "Add a special character"]
    }