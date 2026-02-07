
### Scoring Logic
- **Start at Score**: 0
- **Max Score**: 4

#### Rules
1. **Length**: Length >= 8 chars → (+1 point). Else, add feedback: \"Password is too short\".
2. **Number**: Contains at least one digit (0-9) → (+1 point). Else, add feedback: \"Add a number\".
3. **Uppercase**: Contains at least one uppercase letter (A-Z) → (+1 point). Else, add feedback: \"Add an uppercase letter\".
4. **Special**: Contains at least one special char (!@#$%^&*) → (+1 point). Else, add feedback: \"Add a special character\".

### Output Mapping
- **Score 0-1**: strength: \"Weak\"
- **Score 2-3**: strength: \"Medium\"
- **Score 4**: strength: \"Strong\"

### Edge Cases & Error Handling
1. **Empty String (\"\")**
   - **Input**: `{"password": ""}`
   - **Behavior**: Application must explicitly reject empty passwords.
   - **Status Code**: 400 Bad Request
   - **Response**: `{"detail": "Password cannot be empty"}`
2. **Missing Field**
   - **Input**: `{}` or `{"other_field": "123"}`
   - **Behavior**: Standard validation for missing required field.
   - **Status Code**: 422 Unprocessable Entity
   - **Response**: Standard FastAPI validation error structure.
3. **Null Value**
   - **Input**: `{"password": null}`
   - **Behavior**: Standard validation for invalid type.
   - **Status Code**: 422 Unprocessable Entity
   - **Response**: Standard FastAPI validation error structure.
