# models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    merchant = Column(String, index=True)
    category = Column(String, index=True)
    amount = Column(Integer)
    date = Column(DateTime)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, nullable=False)
    monthly_limit = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
