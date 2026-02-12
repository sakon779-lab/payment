from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()

class PasswordRequest(BaseModel):
    password: str

    @field_validator('password')
    def password_must_not_be_empty(cls, v):
        if not v:
            raise HTTPException(status_code=400, detail="Password cannot be empty")
        return v

@app.post("/check-password")
def check_password(request: PasswordRequest):
    score = 0
    feedback = []

    # Rule 1 (Length)
    if len(request.password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")

    # Rule 2 (Number)
    if any(char.isdigit() for char in request.password):
        score += 1
    else:
        feedback.append("Add a number")

    # Rule 3 (Uppercase)
    if any(char.isupper() for char in request.password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")

    # Rule 4 (Special)
    special_chars = "!@#$%^&*"
    if any(char in special_chars for char in request.password):
        score += 1
    else:
        feedback.append("Add a special character")

    strength_mapping = {
        0: "Weak",
        1: "Weak",
        2: "Medium",
        3: "Medium",
        4: "Strong"
    }

    strength = strength_mapping[score]

    return {"score": score, "strength": strength, "feedback": feedback}