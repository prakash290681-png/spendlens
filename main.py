from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime

from auth import router
from database import engine, SessionLocal
from models import Base, Transaction, Budget


# -------------------- SCHEMAS --------------------
class BudgetIn(BaseModel):
    category: str
    monthly_limit: int


# -------------------- APP SETUP --------------------
app = FastAPI()
app.include_router(router)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


# -------------------- DB DEP --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- ROUTES --------------------
@app.get("/")
def health():
    return {"status": "SpendLens backend running v2"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


@app.get("/summary/monthly")
def monthly_summary(db: Session = Depends(get_db)):
    month = datetime.now().month
    year = datetime.now().year

    results = (
        db.query(
            Transaction.merchant,
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .filter(
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year
        )
        .group_by(
            Transaction.merchant,
            Transaction.category
        )
        .all()
    )

    return {
        "month": f"{month}-{year}",
        "summary": [
            {
                "merchant": r.merchant,
                "category": r.category,
                "total": r.total
            }
            for r in results
        ]
    }


@app.post("/budget")
def set_budget(budget: BudgetIn, db: Session = Depends(get_db)):
    existing = (
        db.query(Budget)
        .filter(Budget.category == budget.category)
        .first()
    )

    if existing:
        existing.monthly_limit = budget.monthly_limit
    else:
        existing = Budget(
            category=budget.category,
            monthly_limit=budget.monthly_limit
        )
        db.add(existing)

    db.commit()

    return {
        "category": existing.category,
        "monthly_limit": existing.monthly_limit
    }


@app.get("/budget")
def get_budgets(db: Session = Depends(get_db)):
    budgets = db.query(Budget).all()

    return [
        {
            "category": b.category,
            "monthly_limit": b.monthly_limit
        }
        for b in budgets
    ]
