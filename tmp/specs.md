# SCRUM-29: Password Strength Checker API

## 1. Functional Requirements
- Endpoint: POST /check-password
- Request Body: `{"password": "string (required)"}`

## 2. Response Schema (Success 200 OK)
Every valid calculation (even for "Weak" passwords) MUST return this JSON structure:
```json
{
  "score": integer,       // 0-4
  "strength": string,     // "Weak", "Medium", "Strong"
  "feedback": [string]    // List of suggestions (e.g., ["Add a number"]) or empty []
}
```

## 3. HTTP Status Code Rules (CRITICAL - DO NOT HALLUCINATE)

### [SUCCESS] 200 OK (Calculation Successful)
- Condition: The input is a valid string (not empty).
- Behavior: The API performs the calculation and returns the JSON result.
- CRITICAL: A "Weak" or "Medium" password is a VALID RESULT, NOT an error.

### [ERROR] 400 Bad Request (Business Validation Error)
- Condition: Input is an Empty String ("") or consists only of whitespace (" ").
- Behavior: Reject immediately.
- Response: {"detail": "Password cannot be empty"}

### [ERROR] 422 Unprocessable Entity (Schema Validation Error)
- Condition: Missing field (no "password" key) or Null value ("password": None).
- Behavior: Standard FastAPI validation error.

## 4. SPEC UPDATE 2026-07-07 (Error Contract Unification)

OVERRIDES section 3 above. To align with the unified error contract introduced in SCRUM-30 (all client errors return HTTP 400 with a flat {"detail": "<message>"} body), the None / missing password case is changed from 422 to 400.

- Empty string "" or whitespace-only → 400 {"detail": "Password cannot be empty"} (unchanged)
- Null "password": None or missing field → 400 {"detail": "Password is required"} (was 422)
- Valid non-empty string → 200 OK with score/strength/feedback (unchanged)

Note to Dev: the global RequestValidationError handler already returns 400 for None; just map the None/type error message to "Password is required" instead of the raw Pydantic default.