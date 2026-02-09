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

from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
import re

# Pydantic Model for Password Check
class PasswordCheck(BaseModel):
    password: str = Field(...)

def check_password_strength(password: str) -> dict:
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append('Password is too short')
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append('Add a number')
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append('Add an uppercase letter')
    
    if re.search(r'[^a-zA-Z0-9]', password):
        score += 1
    else:
        feedback.append('Add a special character')
    
    strength = 'Weak' if score <= 1 else 'Medium' if score <= 3 else 'Strong'
    return {'score': score, 'strength': strength, 'feedback': feedback}

@app.post('/check-password', response_class=JSONResponse)
def check_password(password_check: PasswordCheck):
    if not password_check.password.strip():
        raise HTTPException(status_code=400, detail='Password cannot be empty')
    return check_password_strength(password_check.password)