from fastapi import FastAPI, HTTPException


app = FastAPI()

from pydantic import BaseModel

class PasswordCheckRequest(BaseModel):
    password: str

@app.post('/check-password')
def check_password(request: PasswordCheckRequest):
    password = request.password
    score = 0
    feedback = []

    # Rule 1: Length Check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")

    # Rule 2: Number Check
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append("Add a number")

    # Rule 3: Uppercase Check
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")

    # Rule 4: Special Character Check
    special_characters = "!@#$%^&*"
    if any(char in special_characters for char in password):
        score += 1
    else:
        feedback.append("Add a special character")

    # Strength Mapping
    if 0 <= score <= 1:
        strength = "Weak"
    elif 2 <= score <= 3:
        strength = "Medium"
    else:
        strength = "Strong"

    return {"score": score, "feedback": feedback, "strength": strength}


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