import os
from pathlib import Path

# Configuration of the project structure and file contents
project_structure = {
    "docker-compose.yml": """version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: poc_payment_db
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - ./pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: always
""",
    ".env": """# Database Configuration
DB_USER=postgres
DB_PASSWORD=secretpassword
DB_NAME=payment_poc
DB_HOST=localhost
DB_PORT=5432
""",
    ".gitignore": """__pycache__/
*.py[cod]
.venv/
.env
pg_data/
.DS_Store
.idea/
.vscode/
""",
    "requirements.txt": """fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
""",
    "app/__init__.py": "",
    "app/main.py": """from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 System Starting... Connecting to DB")
    # In the future: await db.connect()
    yield
    print("🛑 System Shutting down...")

app = FastAPI(
    title="Stable Coin Payment Gateway PoC",
    description="PoC system for generating code via LangGraph/Jira Context",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "Payment Gateway Service is Running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "payment-gateway",
        "version": "0.1.0"
    }
""",
    "app/core/__init__.py": "",
    "app/core/config.py": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    @property
    def DATABASE_URL(self):
        # Postgres Async Driver
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()
""",
    "app/db/__init__.py": "",
    "app/services/__init__.py": "",
    "app/schemas/__init__.py": "",
}


def create_project():
    base_path = Path(".")

    print("🚀 Starting Project Generator...")

    for file_path, content in project_structure.items():
        full_path = base_path / file_path

        # Create directories if they don't exist
        if "/" in file_path:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Created: {file_path}")

    print("\n✨ Project Setup Complete! ✨")
    print("Next steps:")
    print("1. python -m venv .venv")
    print("2. source .venv/bin/activate (or .venv\\Scripts\\activate on Windows)")
    print("3. pip install -r requirements.txt")
    print("4. docker-compose up -d")
    print("5. uvicorn app.main:app --reload")


if __name__ == "__main__":
    create_project()