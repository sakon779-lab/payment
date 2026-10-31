"""SQLAlchemy models for the payment service.

`Base` is imported from src.main so this module shares the SAME declarative
base (and therefore the same metadata) as the app engine — a second
declarative_base() would leave the table unregistered and create_all would
never create it.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from datetime import datetime

from src.main import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, nullable=False, index=True)
    payment_address = Column(String, nullable=False)
    amount_expected = Column(Numeric(24, 6), nullable=False)
    status = Column(String, nullable=False, default="PENDING", server_default="PENDING")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )