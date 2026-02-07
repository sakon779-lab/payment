from fastapi import FastAPI, HTTPException

from pydantic import BaseModel

class PasswordCheckRequest(BaseModel):
    password: str

app = FastAPI()

@app.get('/hello/{name}')
def greet(name: str):
    
    return {'message': f'Hello, {name}!'}

@app.get('/reverse/{text}')
def reverse_string(text: str):
    
    return {'original': text, 'reversed': text[::-1]}

@app.post('/check-password')
def check_password(request: PasswordCheckRequest):
    password = request.password
    if not password:
        raise HTTPException(status_code=400, detail='Password cannot be empty')

    score = 0
    feedback = []

    if len(password) >= 8:
        score += 1
    else:
        feedback.append('Password is too short')

    if any(char.isdigit() for char in password):
        score += 1
    else:
        feedback.append('Add a number')

    if any(char.isupper() for char in password):
        score += 1
    else:
        feedback.append('Add an uppercase letter')

    if any(char in '!@#$%^&*' for char in password):
        score += 1
    else:
        feedback.append('Add a special character')

    strength = ''
    if score == 0 or score == 1:
        strength = 'Weak'
    elif score == 2 or score == 3:
        strength = 'Medium'
    else:
        strength = 'Strong'

    return {'score': score, 'strength': strength, 'feedback': feedback}