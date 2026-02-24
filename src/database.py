from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

# Database configuration
DATABASE_URL = "postgresql://postgres:secretpassword@127.0.0.1:5434/shop_db"

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()