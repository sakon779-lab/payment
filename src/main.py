from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
class PasswordRequest(BaseModel):
    password: str

    @field_validator('password')
    def check_empty(cls, v):
        if not v:
            raise HTTPException(status_code=400, detail=['Password cannot be empty'])
        return v
def evaluate_password_strength(password: str) -> dict:
    score = 0
    feedback = []

    # Rule 1 (Length)
    if len(password) >= 8:
        score += 1
    else:
        feedback.append('Password is too short')

    # Rule 2 (Number)
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append('Add a number')

    # Rule 3 (Uppercase)
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append('Add an uppercase letter')

    # Rule 4 (Special)
    if any(char in '!@#$%^&*' for char in password):
        score += 1
    else:
        feedback.append('Add a special character')

    strength = 'Weak'
    if 2 <= score < 4:
        strength = 'Medium'
    elif score == 4:
        strength = 'Strong'

    return {
        'score': score,
        'strength': strength,
        'feedback': feedback
    }
app = FastAPI()
@app.post('/check-password')
def check_password(request: PasswordRequest):
    result = evaluate_password_strength(request.password)
    return result