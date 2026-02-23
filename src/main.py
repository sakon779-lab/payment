from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import re

app = FastAPI()

class PasswordRequest(BaseModel):
    password: str

    @validator('password')
    def password_empty(cls, v):
        if not v.strip():
            raise ValueError("Password cannot be empty")
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

    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password is too short")

    if re.search(r'\d', password):
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

    return {
        "score": score,
        "strength": strength,
        "feedback": feedback
    }

class PaymentRequest(BaseModel):
    amount: float
    currency: str
    payment_method: str

@app.post('/process_payment')
def process_payment(request: PaymentRequest):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment processing failed: Amount must be positive")
    
    return {
        "status": "success",
        "message": "Payment processed successfully"
    }