from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime
from pydantic import BaseModel

from auth import router
from database import engine, SessionLocal
from models import Base, Transaction, Budget

app = FastAPI()
app.include_router(router)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

# ---------- TEMP: RESET DB (REMOVE AFTER USE) ----------
@app.post("/admin/reset-db")
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "db reset"}


# ---------- DB dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Models ----------
class BudgetIn(BaseModel):
    category: str
    monthly_limit: int


# ---------- Health ----------
@app.get("/")
def health():
    return {"status": "SpendLens backend running"}


# ---------- Dashboard ----------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


# ---------- MONTHLY SUMMARY ----------
@app.get("/summary/monthly")
def monthly_summary(
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db)
):
    now = datetime.now()
    target_month = month if month is not None else now.month
    target_year = year if year is not None else now.year

    # Merchant-wise totals
    merchant_rows = (
        db.query(
            Transaction.merchant,
            Transaction.category,
            func.round(func.sum(Transaction.amount), 2).label("total")
        )
        .filter(
            extract("month", Transaction.date) == target_month,
            extract("year", Transaction.date) == target_year
        )
        .group_by(
            Transaction.merchant,
            Transaction.category
        )
        .all()
    )

    # Category totals
    category_rows = (
        db.query(
            Transaction.category,
            func.round(func.sum(Transaction.amount), 2).label("total")
        )
        .filter(
            extract("month", Transaction.date) == target_month,
            extract("year", Transaction.date) == target_year
        )
        .group_by(Transaction.category)
        .all()
    )

    return {
        "month": f"{target_month}-{target_year}",
        "by_merchant": [
            {
                "merchant": r.merchant,
                "category": r.category,
                "total": float(r.total)
            }
            for r in merchant_rows
        ],
        "by_category": [
            {
                "category": r.category,
                "total": float(r.total)
            }
            for r in category_rows
        ]
    }


# ---------- BUDGET ----------
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

@app.get("/alerts/monthly")
def monthly_alerts(
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db)
):
    now = datetime.now()
    m = month or now.month
    y = year or now.year

    spends = (
        db.query(
            Transaction.category,
            func.round(func.sum(Transaction.amount), 2).label("total")
        )
        .filter(
            extract("month", Transaction.date) == m,
            extract("year", Transaction.date) == y
        )
        .group_by(Transaction.category)
        .all()
    )

    budgets = db.query(Budget).all()
    spend_map = {s.category: s.total for s in spends}

    alerts = []
    for b in budgets:
        spent = spend_map.get(b.category, 0)
        if spent >= b.monthly_limit:
            alerts.append({
                "category": b.category,
                "spent": spent,
                "limit": b.monthly_limit
            })

    return {"month": f"{m}-{y}", "alerts": alerts}

