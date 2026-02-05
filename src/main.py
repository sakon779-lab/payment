from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
class PasswordCheckRequest(BaseModel):
    password: str
def check_password_strength(password: str) -> dict:
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
    special_characters = '!@#$%^&*'
    if any(char in special_characters for char in password):
        score += 1
    else:
        feedback.append('Add a special character')
    strength_mapping = {
        (0, 1): 'Weak',
        (2, 3): 'Medium',
        4: 'Strong'
    }
    for range_tuple, strength in strength_mapping.items():
        if isinstance(range_tuple, tuple):
            if range_tuple[0] <= score <= range_tuple[1]:
                return {'strength': strength, 'score': score, 'feedback': feedback}
        elif score == range_tuple:
            return {'strength': strength, 'score': score, 'feedback': feedback}
    return {'strength': 'Unknown', 'score': score, 'feedback': feedback}

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

@app.post('/check-password')
def check_password(request: PasswordCheckRequest):
    if not request.password:
        raise HTTPException(status_code=400, detail='Password cannot be empty')
    result = check_password_strength(request.password)
    return result