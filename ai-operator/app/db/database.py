import os
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_operator.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ApprovalORM(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    proposed_command = Column(String, nullable=False)
    cwd = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RunORM(Base):
    __tablename__ = "runs"
    id = Column(String, primary_key=True, index=True)
    approval_id = Column(String, index=True)
    command = Column(String, nullable=False)
    cwd = Column(String, nullable=False)
    returncode = Column(Integer, nullable=False)
    ok = Column(Boolean, nullable=False)
    stdout = Column(Text)
    stderr = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
