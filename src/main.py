from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()

class PasswordRequest(BaseModel):
    password: str
    
    @field_validator('password')
    def check_empty(cls, v):
        if not v.strip():
            raise HTTPException(status_code=400, detail="Password cannot be empty")
        return v

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
    password = request.password
    score = 0
    feedback = []

    # Rule 1: Length
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")

    # Rule 2: Number
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append("Add a number")

    # Rule 3: Uppercase
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")

    # Rule 4: Special
    special_chars = "!@#$%^&*"
    if any(char in special_chars for char in password):
        score += 1
    else:
        feedback.append("Add a special character")

    strength_mapping = {
        (0, 1): "Weak",
        (2, 3): "Medium",
        (4,): "Strong"
    }

    for range_tuple, strength in strength_mapping.items():
        if score in range_tuple:
            return {"score": score, "strength": strength, "feedback": feedback}

    raise HTTPException(status_code=500, detail="Unexpected error occurred")