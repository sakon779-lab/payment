from fastapi import FastAPI
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
