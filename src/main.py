
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
class PasswordCheckRequest(BaseModel):
    password: str
app = FastAPI()

def check_password_strength(password: str) -> dict:
    score = 0
    feedback = []
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")
    if re.search(r'[0-9]', password):
        score += 1
    else:
        feedback.append("Add a number")
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")
    if re.search(r'[!@#$%^&*]', password):
        score += 1
    else:
        feedback.append("Add a special character")
    strength = "Weak" if score <= 1 else "Medium" if score <= 3 else "Strong"
    return {"score": score, "strength": strength, "feedback": feedback}

@app.post('/check-password')
def check_password(request: PasswordCheckRequest):
    password = request.password
    if not password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    result = check_password_strength(password)
    return result
