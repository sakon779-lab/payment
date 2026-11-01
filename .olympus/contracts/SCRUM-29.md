# Design Contract — SCRUM-29

> Implement Password Strength Checker API

## Endpoints
- `POST /check-password`

## Request
```json
{
  "password": "string (required)"
}
```

## Success
```json
{
  "status": 200,
  "body": {
    "score": "int 0-4",
    "strength": "Weak|Medium|Strong",
    "feedback": "[string]"
  }
}
```

## Error contract
- **password missing or null** → `400` `{"detail": "Password is required"}`
- **password empty string or whitespace-only** → `400` `{"detail": "Password cannot be empty"}`

## Business rules
- Start at Score = 0. Max Score = 4 (Additive only).
- Length >= 8 chars → (+1 point). Else: feedback 'Password is too short'.
- Contains digit (0-9) → (+1 point). Else: feedback 'Add a number'.
- Contains uppercase (A-Z) → (+1 point). Else: feedback 'Add an uppercase letter'.
- Contains special char (!@#$%^&*) → (+1 point). Else: feedback 'Add a special character'.
- Score 0-1: strength: 'Weak'
- Score 2-3: strength: 'Medium'
- Score 4: strength: 'Strong'

## Edge cases
- password length exactly 8
- password empty string
- password whitespace-only
- password with special characters and digits
- password without any uppercase letters

## Worked examples (oracle)
- `{"password": "StrongP@ss1"}` → `{"score": 4, "strength": "Strong", "feedback": []}`
- `{"password": "Abc123"}` → `{"score": 2, "strength": "Medium", "feedback": ["Password is too short", "Add a special character"]}`
- `{"password": ""}` → `{"status": 400, "body": {"detail": "Password cannot be empty"}}`

## Files to touch
- src/main.py

## Out of scope (regression guard)
- the shared RequestValidationError handler used by /checkout must keep its own messages
