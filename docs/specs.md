## 3. 🧠 Scoring Logic (Business Rules)

### Base:
- Start at Score = 0. Max Score = 4. (Additive only).

### Rules:
1. **Length:** Length >= 8 chars → (+1 point). Else: feedback "Password is too short".
2. **Number:** Contains digit (0-9) → (+1 point). Else: feedback "Add a number".
3. **Uppercase:** Contains uppercase (A-Z) → (+1 point). Else: feedback "Add an uppercase letter".
4. **Special:** Contains special char (!@#$%^&*) → (+1 point). Else: feedback "Add a special character".

## 4. 📊 Output Mapping (Business Logic)

- **Score 0-1:** strength: "Weak"
- **Score 2-3:** strength: "Medium"
- **Score 4:** strength: "Strong"

## 5. [SUCCESS] HTTP Status Code Rules (CRITICAL - DO NOT HALLUCINATE)

### [SUCCESS] 200 OK (Calculation Successful)
- **Condition:** The input is a valid string (not empty).
- **Behavior:** The API performs the calculation and returns the JSON result.
- **CRITICAL:** A "Weak" or "Medium" password is a VALID RESULT, NOT an error.

#### Example:
- **password: "123"** → Returns 200 OK with `{ "strength": "Weak" ... }`
- **password: "P@ssw0rd1"** → Returns 200 OK with `{ "strength": "Strong" ... }`

### [ERROR] 400 Bad Request (Business Validation Error)
- **Condition:** Input is an Empty String (`""`) or consists only of whitespace (`" "`).
- **Behavior:** Reject immediately.
- **Response:** `{"detail": "Password cannot be empty"}`
- **Note to Dev:** You must check `if not password.strip():` inside a validator.

### [ERROR] 422 Unprocessable Entity (Schema Validation Error)
- **Condition:** Missing field (no `password` key) or Null value (`"password": null`).
- **Behavior:** Standard FastAPI validation error.