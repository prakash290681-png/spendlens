# models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, UniqueConstraint
from datetime import datetime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    merchant = Column(String)
    category = Column(String)
    amount = Column(Float)
    date = Column(DateTime)

# 👇 ADD THIS
    source_id = Column(String, unique=True, index=True)

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, nullable=False)
    monthly_limit = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
