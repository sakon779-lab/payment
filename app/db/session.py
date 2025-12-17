import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# โหลดค่าจาก .env ให้มั่นใจว่ามีค่ามาแน่นอน
load_dotenv()

# 1. ดึงค่า Config
USER = os.getenv("DB_USER", "postgres")
PASSWORD = os.getenv("DB_PASSWORD", "secretpassword")
SERVER = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "5432")
DB = os.getenv("DB_NAME", "payment_poc")

# 2. สร้าง URL Connection String
SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{SERVER}:{PORT}/{DB}"

# 3. สร้าง Engine (ตัวขับเคลื่อนหลัก)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. สร้าง Session Factory (ตัวแจกจ่าย Session ให้ Agent ใช้)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)