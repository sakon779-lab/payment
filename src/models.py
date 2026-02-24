from pydantic import BaseModel, validator
from typing import Optional


class CheckoutRequest(BaseModel):
    user_id: int
    product_id: str
    amount: float

    @validator('user_id')
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('user_id must be a positive integer')
        return v

    @validator('product_id')
    def validate_product_id(cls, v):
        if not v or not v.strip():
            raise ValueError('product_id cannot be empty')
        return v

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('amount must be strictly greater than 0')
        return v

class OrderResponse(BaseModel):
    order_status: str

class PaymentErrorResponse(BaseModel):
    error: str

class UserNotFoundError(BaseModel):
    detail: str