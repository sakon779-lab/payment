# SCRUM-29: Fix Password Validation

## Problem
The previous implementation of the global RequestValidationError handler changed the shared "if error_type == missing" branch to always return "Password is required", which broke other endpoints that rely on the original behavior.

## Requirements
1. Only the password field should return "Password is required" for missing/None values
2. Other fields (user_id, product_id, amount) should continue to return "{field} is required" messages
3. Empty/whitespace passwords should return "Password cannot be empty"
4. Valid passwords should return 200 with score/strength/feedback

## Solution
Modify the exception handler in src/main.py to scope the change to the password field only:

```python
if field_name == "password" and error_type in ("missing", "string_type"):
    custom_msg = "Password is required"
elif error_type == "missing":
    custom_msg = f"{field_name} is required"   # UNCHANGED for other fields
else:
    custom_msg = error_msg.replace("Value error, ", "")
```

## Test Cases
- POST /check-password with None password → 400 "Password is required"
- POST /check-password with missing password field → 400 "Password is required"
- POST /check-password with empty password → 400 "Password cannot be empty"
- POST /check-password with whitespace-only password → 400 "Password cannot be empty"
- POST /check-password with valid password → 200 with score/strength/feedback
- POST /api/v1/checkout with missing user_id → 400 "user_id is required" (unchanged)
- POST /api/v1/checkout with missing product_id → 400 "product_id is required" (unchanged)
- POST /api/v1/checkout with missing amount → 400 "amount is required" (unchanged)