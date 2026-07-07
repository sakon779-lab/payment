from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

# Test the specific cases mentioned in the ticket
def test_password_validation_cases():
    # Test null password -> 400 with "Password is required"
    response = client.post("/check-password", json={"password": None})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password is required"}
    print("✓ Null password test passed")
    
    # Test missing password field -> 400 with "Password is required"
    response = client.post("/check-password", json={})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password is required"}
    print("✓ Missing password field test passed")
    
    # Test empty string -> 400 with "Password cannot be empty"
    response = client.post("/check-password", json={"password": ""})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}
    print("✓ Empty string test passed")
    
    # Test whitespace-only -> 400 with "Password cannot be empty"
    response = client.post("/check-password", json={"password": "   "})
    assert response.status_code == 400
    assert response.json() == {"detail": "Password cannot be empty"}
    print("✓ Whitespace-only test passed")
    
    # Test valid password -> 200
    response = client.post("/check-password", json={"password": "StrongP@ss1"})
    assert response.status_code == 200
    assert "score" in response.json()
    assert "strength" in response.json()
    assert "feedback" in response.json()
    print("✓ Valid password test passed")

if __name__ == "__main__":
    test_password_validation_cases()
    print("All tests passed successfully!")