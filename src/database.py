from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:secretpassword@127.0.0.1:5434/shop_db")

# Create the engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Import all models here to ensure they are registered with the Base
    from src.models import CheckoutRequest, OrderResponse, PaymentErrorResponse, UserNotFoundError
    # Create all tables
    Base.metadata.create_all(bind=engine)