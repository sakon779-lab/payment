from fastapi import FastAPI, HTTPException

app = FastAPI()

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
from pydantic import BaseModel

class PasswordCheckRequest(BaseModel):
    password: str

def check_password_strength(password: str) -> dict:
    score = 0
    feedback = []

    # Rule 1: Length >= 8 chars
    if len(password) >= 8:
        score += 1
    else:
        feedback.append('Password is too short')

    # Rule 2: Contains at least one digit (0-9)
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append('Add a number')

    # Rule 3: Contains at least one uppercase letter (A-Z)
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append('Add an uppercase letter')

    # Rule 4: Contains at least one special character (!@#$%^&*)
    special_characters = '!@#$%^&*'
    if any(char in special_characters for char in password):
        score += 1
    else:
        feedback.append('Add a special character')

    # Output Mapping
    if score <= 1:
        strength = 'Weak'
    elif score <= 3:
        strength = 'Medium'
    else:
        strength = 'Strong'

    return {
        'score': score,
        'feedback': feedback,
        'strength': strength
    }

@app.post('/check-password')
def check_password(request: PasswordCheckRequest):
    if not request.password.strip():
        raise HTTPException(status_code=400, detail='Password cannot be empty')
    return check_password_strength(request.password)