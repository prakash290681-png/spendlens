from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
from datetime import datetime


# ----------------------------
# User model (Phase 2A)
# ----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------
# Transaction model (existing)
# ----------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    merchant = Column(String, index=True)
    category = Column(String, index=True)
    amount = Column(Float)

    date = Column(DateTime, index=True)

    # Used to prevent duplicate inserts from emails
    source_id = Column(String, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
