from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import httpx
import os
import re

# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:secretpassword@127.0.0.1:5434/shop_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI()

# Database models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class CheckoutRequest(BaseModel):
    user_id: int
    product_id: str
    amount: float

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('user_id must be a positive integer')
        return v

    @field_validator('product_id')
    @classmethod
    def validate_product_id(cls, v):
        if not v or not v.strip():
            raise ValueError('product_id cannot be empty')
        return v

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('amount must be strictly greater than 0')
        return v

class CheckoutResponse(BaseModel):
    order_status: str

class PaymentErrorResponse(BaseModel):
    error: str

# API endpoints
@app.post("/api/v1/checkout", response_model=CheckoutResponse)
async def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Call external payment gateway
    payment_url = "http://127.0.0.1:1080/external/payment/charge"
    async with httpx.AsyncClient() as client:
        payment_response = await client.post(
            payment_url,
            json={
                "user_id": request.user_id,
                "product_id": request.product_id,
                "amount": request.amount
            }
        )

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
        raise HTTPException(status_code=402, detail="Payment Declined")
    else:
        # Other error
        raise HTTPException(status_code=400, detail="Payment processing failed")

# Existing endpoints (keep them)
class PasswordRequest(BaseModel):
    password: str

    @field_validator('password')
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