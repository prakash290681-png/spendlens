from fastapi import APIRouter
from database import SessionLocal
from models import Transaction
from sqlalchemy import Date
from datetime import timezone

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/cleanup-swiggy")
def cleanup_swiggy():
    """
    Remove duplicate Swiggy rows:
    rule = same UTC date + same amount
    """
    db = SessionLocal()
    deleted = 0

    try:
        rows = (
            db.query(Transaction)
            .filter(Transaction.merchant == "Swiggy")
            .order_by(Transaction.date, Transaction.id)
            .all()
        )

        seen = set()

        for tx in rows:
            key = (
                tx.date.astimezone(timezone.utc).date(),
                round(float(tx.amount), 2),
            )

            if key in seen:
                db.delete(tx)
                deleted += 1
            else:
                seen.add(key)

        db.commit()
        return {
            "status": "ok",
            "deleted_duplicates": deleted,
        }

    finally:
        db.close()


@router.post("/cleanup-zomato")
def cleanup_zomato():
    """
    Optional manual cleanup for Zomato
    """
    db = SessionLocal()
    deleted = 0

    try:
        rows = (
            db.query(Transaction)
            .filter(Transaction.merchant == "Zomato")
            .order_by(Transaction.date, Transaction.id)
            .all()
        )

        seen = set()

        for tx in rows:
            key = (
                tx.date.astimezone(timezone.utc).date(),
                round(float(tx.amount), 2),
            )

            if key in seen:
                db.delete(tx)
                deleted += 1
            else:
                seen.add(key)

        db.commit()
        return {
            "merchant": "Zomato",
            "deleted_duplicates": deleted,
        }

    finally:
        db.close()
