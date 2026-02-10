from fastapi import APIRouter
from database import SessionLocal
from models import Transaction
from datetime import timezone

router = APIRouter(prefix="/admin", tags=["admin"])


# -------------------------------------------------
# Swiggy duplicate cleanup
# Rule:
# Same user + Swiggy + same calendar day + same amount
# -------------------------------------------------
@router.get("/cleanup-swiggy-duplicates")
def cleanup_swiggy_duplicates():
    db = SessionLocal()
    deleted = 0

    rows = (
        db.query(Transaction)
        .filter(Transaction.merchant == "Swiggy")
        .order_by(Transaction.user_id, Transaction.date)
        .all()
    )

    seen = {}

    for tx in rows:
        key = (
            tx.user_id,
            tx.date.astimezone(timezone.utc).date(),
            round(float(tx.amount), 2),
        )

        if key in seen:
            db.delete(tx)
            deleted += 1
        else:
            seen[key] = tx

    db.commit()
    db.close()

    return {
        "merchant": "Swiggy",
        "deleted_duplicates": deleted,
    }


# -------------------------------------------------
# Zomato duplicate cleanup
# Rule:
# Same user + Zomato + same calendar day + same amount
# -------------------------------------------------
@router.get("/cleanup-zomato-duplicates")
def cleanup_zomato_duplicates():
    db = SessionLocal()
    deleted = 0

    rows = (
        db.query(Transaction)
        .filter(Transaction.merchant == "Zomato")
        .order_by(Transaction.user_id, Transaction.date)
        .all()
    )

    seen = {}

    for tx in rows:
        key = (
            tx.user_id,
            tx.date.astimezone(timezone.utc).date(),
            round(float(tx.amount), 2),
        )

        if key in seen:
            db.delete(tx)
            deleted += 1
        else:
            seen[key] = tx

    db.commit()
    db.close()

    return {
        "merchant": "Zomato",
        "deleted_duplicates": deleted,
    }
