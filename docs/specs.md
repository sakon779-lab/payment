
## Business Logic & Rules

1. **Score Initialization**: Start at score = 0, max score = 4.
2. **Length Rule**: If the password length is >= 8 characters → (+1 point). Else, add feedback: `"Password is too short"`.
3. **Number Rule**: If the password contains at least one digit (0-9) → (+1 point). Else, add feedback: `"Add a number"`.
4. **Uppercase Rule**: If the password contains at least one uppercase letter (A-Z) → (+1 point). Else, add feedback: `"Add an uppercase letter"`.
5. **Special Character Rule**: If the password contains at least one special character (!@#$%^&*) → (+1 point). Else, add feedback: `"Add a special character"`.
6. **Strength Mapping**:
   - Score 0-1: `strength = "Weak"`
   - Score 2-3: `strength = "Medium"`
   - Score 4: `strength = "Strong"`

## Edge Cases & Error Handling
- **Empty String**: Return 400 Bad Request with a custom error message.
- **Missing Field**: Standard FastAPI validation returns 422 Unprocessable Entity.
- **Null Value**: Standard FastAPI validation returns 422 Unprocessable Entity.
