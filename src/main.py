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


# Import models and database
from src.models import Base, User, Order, get_db
from src.database import engine
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import os


class CheckoutRequest(BaseModel):
    user_id: int
    product_id: str
    amount: float


class CheckoutResponse(BaseModel):
    order_status: str


class PaymentErrorResponse(BaseModel):
    error: str


class UserNotFoundError(BaseModel):
    detail: str


def validate_checkout_request(request: CheckoutRequest):
    if request.user_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="user_id must be a positive integer"
        )
    
    if not request.product_id:
        raise HTTPException(
            status_code=400,
            detail="product_id cannot be empty"
        )
    
    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="amount must be strictly greater than 0"
        )


@ app.post("/api/v1/checkout", response_model=CheckoutResponse, status_code=201)
async def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    # Validate input
    validate_checkout_request(request)
    
    # Check if user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Call external payment gateway
    payment_url = os.getenv("PAYMENT_GATEWAY_URL", "http://127.0.0.1:1080/external/payment/charge")
    
    async with httpx.AsyncClient() as client:
        try:
            payment_response = await client.post(
                payment_url,
                json={
                    "user_id": request.user_id,
                    "amount": request.amount
                }
            )
        except Exception as e:
            # If payment gateway is unreachable, treat as payment declined
            raise HTTPException(
                status_code=402,
                detail="Payment Declined"
            )
    
    # Process payment result
    if payment_response.status_code == 200:
        # Payment successful, create order
        order = Order(
            user_id=request.user_id,
            product_id=request.product_id,
            amount=request.amount,
            status="COMPLETED"
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        return CheckoutResponse(order_status="COMPLETED")
    
    elif payment_response.status_code == 400:
        # Payment declined
        raise HTTPException(
            status_code=402,
            detail="Payment Declined"
        )
    
    else:
        # Other error
        raise HTTPException(
            status_code=402,
            detail="Payment Declined"
        )


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)