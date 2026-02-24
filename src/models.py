from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), Noneable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, Noneable=False)
    product_id = Column(String(50), Noneable=False)
    amount = Column(Float, Noneable=False)
    status = Column(String(50), Noneable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
