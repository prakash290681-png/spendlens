from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    merchant = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), index=True, nullable=False)

    source_id = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transactions")

    # ✅ dedup only by user_id + source_id (your original working logic)
    __table_args__ = (
        UniqueConstraint("user_id", "source_id", name="uq_user_source"),
    )
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    event_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)