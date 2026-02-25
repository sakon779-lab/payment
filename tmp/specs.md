# SCRUM-30: Implement Order Checkout API with External Payment Gateway

## Summary
Implement a new API endpoint `/api/v1/checkout` that allows users to submit orders for payment processing via an external payment gateway.

## Technical Specifications
- **Endpoint**: `POST /api/v1/checkout`
- **Request Payload**:
```json
{
  "user_id": 999,
  "product_id": "PROD-01",
  "amount": 1500.00
}
```

## Input Validation Rules
If any validation fails, the API MUST return `400 Bad Request` with the exact JSON structure: `{"detail": "<Exact_Error_Message>"}`

### Validation Rules
1. `user_id`: Required. Must be a positive integer (> 0)
   - Error if missing: `{"detail": "user_id is required"}`
   - Error if <= 0: `{"detail": "user_id must be a positive integer"}`

2. `product_id`: Required. Must be a string and cannot be empty or None
   - Error if missing: `{"detail": "product_id is required"}`
   - Error if empty/None: `{"detail": "product_id cannot be empty"}`

3. `amount`: Required. Must be a decimal number strictly greater than 0
   - Error if missing: `{"detail": "amount is required"}`
   - Error if <= 0: `{"detail": "amount must be strictly greater than 0"}`

## Database Information
- **Connection**: DB_HOST=127.0.0.1, DB_PORT=5434, DB_NAME=shop_db, DB_USER=postgres, DB_PASS=secretpassword
- **Table `users`**: Needs an active user to proceed
- **Table `orders`**: The API will insert a record here upon successful payment

## Mock Server Information
- **Mock Server URL**: `http://127.0.0.1:1080`
- **External API to Mock**: `POST /external/payment/charge`
- **Expected Mock Response (Success)**: HTTP 200 `{"status": "SUCCESS", "txn_id": "mock_txn_888"}`
- **Expected Mock Response (Failed)**: HTTP 400 `{"status": "DECLINED", "reason": "Insufficient Funds"}`

## Acceptance Criteria
### AC1 - Successful Checkout (Happy Path)
- Given a valid user exists in the database
- And the Mock Payment Gateway is set up to return 200 OK (SUCCESS)
- When calling POST /api/v1/checkout with valid payload
- Then the API should return 201 Created
- And the response JSON should contain `{"order_status": "COMPLETED"}`

### AC2 - Payment Declined
- Given a valid user exists in the database
- And the Mock Payment Gateway is set up to return 400 Bad Request (DECLINED)
- When calling POST /api/v1/checkout
- Then the API should return 402 Payment Required
- And the response JSON should contain `{"error": "Payment Declined"}`

### AC3 - User Not Found
- Given a `user_id` does NOT exist in the database
- When calling POST /api/v1/checkout
- Then the API should return 404 Not Found
- And the response JSON should contain `{"detail": "User not found"}`