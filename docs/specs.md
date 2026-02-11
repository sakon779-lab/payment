
## Scoring Logic (Business Rules)
Start at Score = 0. Max Score = 4. (Add points only. Do NOT subtract points. Minimum score is 0.)
- **Rule 1 (Length):** Length >= 8 chars → (+1 point). Else, add feedback: *\"Password is too short\"*.
- **Rule 2 (Number):** Contains at least one digit (0-9) → (+1 point). Else, add feedback: *\"Add a number\"*.
- **Rule 3 (Uppercase):** Contains at least one uppercase letter (A-Z) → (+1 point). Else, add feedback: *\"Add an uppercase letter\"*.
- **Rule 4 (Special):** Contains at least one special char (!@#$%^&*) → (+1 point). Else, add feedback: *\"Add a special character\"*.

## Output Mapping
- Score 0-1: `strength: "Weak"`
- Score 2-3: `strength: "Medium"`
- Score 4: `strength: "Strong"`

## Edge Cases & Error Handling
### Empty String ("")
- **Input:** `{"password": ""}`
- **Behavior:** Application must explicitly reject empty passwords.
- **Status Code:** `400 Bad Request` (Do NOT return 422).
- **Response:** `{"detail": "Password cannot be empty"}`

### Missing Field
- **Input:** `{}` (Empty JSON) or `{"other_field": "123"}`
- **Behavior:** Standard validation for missing required field.
- **Status Code:** `422 Unprocessable Entity`
- **Response:** Standard FastAPI validation error structure.

### Null Value
- **Input:** `{"password": null}`
- **Behavior:** Standard validation for invalid type.
- **Status Code:** `422 Unprocessable Entity`

## Technical Constraints
- Modify `src/main.py`
- Use Pydantic models for validation.
