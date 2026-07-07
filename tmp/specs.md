# SCRUM-29 Password Validation Specification

## Overview
This specification defines the behavior of the `/check-password` endpoint's validation logic, particularly for handling None and missing password fields.

## Requirements

### 1. Valid Password (200 OK)
- A valid non-empty string should return HTTP 200 with the password strength calculation

### 2. Invalid Password Cases (400 Bad Request)

#### Case 1: Null Password
- Input: `{"password": None}`
- Expected: HTTP 400 with `"detail": "Password is required"`

#### Case 2: Missing Password Field
- Input: `{}`
- Expected: HTTP 400 with `"detail": "Password is required"`

#### Case 3: Empty or Whitespace-only Password
- Input: `{"password": ""}` or `{"password": "   "}`
- Expected: HTTP 400 with `"detail": "Password cannot be empty"`

## Implementation Notes

### Error Handling
- Pydantic v2 reports error type "string_type" for a None value on a str field
- Pydantic v2 reports error type "missing" for an absent field
- Both cases must return "Password is required" with a capital P

### Current Code Status
The existing `@app.exception_handler(RequestValidationError)` in `src/main.py` already handles None values correctly by returning 400, but we need to ensure both None and missing field cases return the same error message "Password is required" instead of the default Pydantic messages.

### Test Coverage
The test file `tests/test_password_validation.py` must cover all the above cases.