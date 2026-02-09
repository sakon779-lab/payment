# from fastapi.testclient import TestClient
# from src.main import app

# test_client = TestClient(app)

# def test_hello_endpoint():
#     response = test_client.get('/hello/World')
#     assert response.status_code == 200
#     assert response.json() == {'message': 'Hello, World!'}

# def test_hello_valid_name():
#     response = test_client.get('/hello/Alice')
#     assert response.status_code == 200
#     assert response.json() == {'message': 'Hello, Alice!'}

# def test_hello_invalid_name():
#     response = test_client.get('/hello/Al1ce')
#     assert response.status_code == 400
#     assert response.json() == {'detail': 'Name must contain only alphabets'}

# def test_reverse_valid_text():
#     response = test_client.get('/reverse/hello')
#     assert response.status_code == 200
#     assert response.json() == {'original': 'hello', 'reversed': 'olleh'}

# def test_reverse_invalid_text():
#     response = test_client.get('/reverse/   ')
#     assert response.status_code == 400
#     assert response.json() == {'detail': 'Text cannot be empty or contain only spaces'}