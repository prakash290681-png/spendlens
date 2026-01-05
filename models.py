# models.py
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    merchant = Column(String, index=True)
    category = Column(String, index=True)
    amount = Column(Integer)
    date = Column(DateTime)
