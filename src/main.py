from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI()

@app.post('/check-password')
async def check_password(request: Request):
    payload = await request.json()
    
    if 'password' not in payload or not isinstance(payload['password'], str):
        raise HTTPException(status_code=422, detail='Invalid input type')
    
    password = payload['password']
    
    if not password:
        raise HTTPException(status_code=400, detail='Password cannot be empty')
    
    score = 0
    feedback = []
    
    # Rule 1: Length >= 8 chars
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")
    
    # Rule 2: Contains at least one digit (0-9)
    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append("Add a number")
    
    # Rule 3: Contains at least one uppercase letter (A-Z)
    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append("Add an uppercase letter")
    
    # Rule 4: Contains at least one special char (!@#$%^&*)
    special_chars = "!@#$%^&*"
    if any(char in special_chars for char in password):
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
    
    return {
        "score": score,
        "feedback": feedback,
        "strength": strength
    }

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
