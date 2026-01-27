from fastapi import APIRouter
from database import SessionLocal
from models import Transaction

router = APIRouter(prefix="/admin")

@router.post("/reset-db")
def reset_db():
    db = SessionLocal()
    try:
        db.query(Transaction).delete()
        db.commit()
        return {"status": "ok", "message": "transactions table cleared"}
    finally:
        db.close()
