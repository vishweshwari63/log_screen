import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL URL structure: postgresql://username:password@host:port/database
# Fallback to a local SQLite database for development ease if no Postgres URL is configured
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://crm_user:crm_password@localhost:5432/crm_db"
)

# Connect args are only needed for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
