from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()

class PasswordRequest(BaseModel):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if not v.strip():
            raise ValueError('Password cannot be empty')
        return v

def calculate_strength(password: str):
    score = 0
    feedback = []

    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")

    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append("Add a number")

    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")

    if any(char in "!@#$%^&*" for char in password):
        score += 1
    else:
        feedback.append("Add a special character")

    if score <= 1:
        strength = "Weak"
    elif score <= 3:
        strength = "Medium"
    else:
        strength = "Strong"

    return {"score": score, "strength": strength, "feedback": feedback}

@app.get('/hello/{name}')
def greet(name: str):
    if not name.isalpha():
        raise HTTPException(status_code=400, detail='Name must contain only alphabets')
    return {'message': f'Hello, {name}!'}

@app.get('/reverse/{text}')
def reverse_string(text: str):
    if not text.strip():
        raise HTTPException(status_code=400, detail='Text cannot be empty or contain only spaces')
    return {'original': text, 'reversed': text[::-1]}

@app.post('/check-password')
def check_password(request: PasswordRequest):
    result = calculate_strength(request.password)
    return result