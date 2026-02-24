from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, validator
import re
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import httpx
import os

app = FastAPI()

# Import dependencies
from src.models import CheckoutRequest, OrderResponse, PaymentErrorResponse, UserNotFoundError
from src.database import get_db, create_tables


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


def get_payment_gateway_url():
    return os.getenv("PAYMENT_GATEWAY_URL", "http://127.0.0.1:1080/external/payment/charge")


@app.on_event("startup")
async def startup_event():
    create_tables()


@app.post("/api/v1/checkout", response_model=OrderResponse)
async def checkout(request: CheckoutRequest, db: Session = Depends(get_db)):
    # Validate that the user exists
    user = db.execute("SELECT id FROM users WHERE id = :user_id", {"user_id": request.user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Call external payment gateway
    payment_url = get_payment_gateway_url()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                payment_url,
                json={
                    "user_id": request.user_id,
                    "product_id": request.product_id,
                    "amount": request.amount
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Payment gateway error")

    # Check payment result
    if response.status_code == 200:
        # Payment successful, create order
        try:
            db.execute(
                "INSERT INTO orders (user_id, product_id, amount, status) VALUES (:user_id, :product_id, :amount, 'COMPLETED')",
                {
                    "user_id": request.user_id,
                    "product_id": request.product_id,
                    "amount": request.amount
                }
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database error while creating order")

        return OrderResponse(order_status="COMPLETED")
    elif response.status_code == 400:
        # Payment declined
        return PaymentErrorResponse(error="Payment Declined")
    else:
        # Other error
        raise HTTPException(status_code=500, detail="Payment gateway error")