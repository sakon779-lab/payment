# SCRUM-29: Password Strength Checker API

## Requirements

### Endpoint
- POST /check-password
- Request Body: {"password": "string (required)"}

### Response Schema (Success 200 OK)
Every valid calculation (even for "Weak" passwords) MUST return this JSON structure:
```json
{
  "score": integer,       // 0-4
  "strength": string,     // "Weak", "Medium", "Strong"
  "feedback": [string]    // List of suggestions (e.g., ["Add a number"]) or empty []
}
```

### Error Handling

#### 400 Bad Request (Business Validation Error)
- Condition: Input is an Empty String ("") or consists only of whitespace (" ").
- Behavior: Reject immediately.
- Response: {"detail": "Password cannot be empty"}

#### 400 Bad Request (Schema Validation Error)
- Condition: Missing field (no "password" key) or Null value ("password": None).
- Behavior: Return HTTP 400 with message "Password is required" (capital P)

#### 200 OK (Calculation Successful)
- Condition: The input is a valid string (not empty).
- Behavior: The API performs the calculation and returns the JSON result.

### Validation Logic
- Password must not be empty or whitespace-only
- Score calculation based on: length, number, uppercase, special character

### Note
The global RequestValidationError handler already returns 400 for None values; we need to ensure that both None values and missing fields return the message "Password is required" with a capital P instead of the raw Pydantic default.