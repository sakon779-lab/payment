from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

# Test missing field
print("=== Testing missing field ===")
response = client.post("/check-password", json={})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test null value
print("\n=== Testing null value ===")
response = client.post("/check-password", json={"password": None})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")