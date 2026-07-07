"""Pytest test isolation — never touch the real database.

src/main.py reads DATABASE_URL at import time and calls
Base.metadata.create_all(bind=engine) at module scope, so importing the app
would otherwise connect to the real Postgres ("db" host, only reachable inside
docker-compose). Point every pytest run at an in-memory SQLite DB *before* any
test imports src.main, per the project's testing standard (unit tests must run
against an in-memory DB, never the real one).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
