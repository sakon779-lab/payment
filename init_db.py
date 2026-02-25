from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import Base

# Create in-memory database for testing
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

print("Database initialized successfully")