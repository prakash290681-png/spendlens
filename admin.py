from fastapi import APIRouter
from database import SessionLocal
from models import Transaction
from sqlalchemy import func, Date

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/cleanup-swiggy")
def cleanup_swiggy():
    """
    Remove duplicate Swiggy rows.
    Rule: keep ONE row per (date + amount)
    """
    db = SessionLocal()
    deleted = 0

    try:
        rows = (
            db.query(Transaction)
            .filter(Transaction.merchant == "Swiggy")
            .order_by(Transaction.date)
            .all()
        )

        seen = set()
        
        for row in rows:
            key = (float(row.amount), row.date.date())

            if key in seen:
                db.delete(row)
                deleted += 1
            else:
                seen.add(key)
        db.commit()
        return {
            "status": "ok",
            "deleted_duplicates": deleted
        }
    finally:
        db.close()


@router.post("/cleanup-zomato")
def cleanup_zomato():
    """
    Optional: same dedupe for Zomato
    """
    db = SessionLocal()

    rows = (
        db.query(Transaction)
        .filter(Transaction.merchant == "Zomato")
        .order_by(Transaction.date)
        .all()
    )

    seen = set()
    deleted = 0

    for row in rows:
        key = (float(row.amount), row.date.date())

        if key in seen:
            db.delete(row)
            deleted += 1
        else:
            seen.add(key)

    db.commit()
    db.close()

    return {
        "merchant": "Zomato",
        "deleted_duplicates": deleted
    }
