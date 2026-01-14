from dotenv import load_dotenv
load_dotenv()

from models import Budget
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


# ---------- Routes ----------
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
def monthly_summary():
    db: Session = SessionLocal()

    month = datetime.now().month
    year = datetime.now().year

    # 🔍 DEBUG 1: total rows in DB
    total_rows = db.query(Transaction).count()
    print("TOTAL TX IN DB:", total_rows)

    # 🔍 DEBUG 2: show sample dates
    sample_dates = db.query(Transaction.date).limit(5).all()
    print("SAMPLE TX DATES:", sample_dates)

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

    db.close()

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

from models import Budget

@app.get("/alerts/monthly")
def monthly_alerts(db: Session = Depends(get_db)):
    month = datetime.now().month
    year = datetime.now().year

    # 1️⃣ Total spend per category (current month)
    spends = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .filter(
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year
        )
        .group_by(Transaction.category)
        .all()
    )

    spend_map = {s.category: s.total for s in spends}

    # 2️⃣ Budgets
    budgets = db.query(Budget).all()

    alerts = []

    for b in budgets:
        spent = spend_map.get(b.category, 0)
        limit = b.monthly_limit

        if spent == 0:
            continue

        percent = int((spent / limit) * 100)

        if percent >= 100:
            status = "exceeded"
        elif percent >= 80:
            status = "warning"
        else:
            continue

        alerts.append({
            "category": b.category,
            "spent": spent,
            "limit": limit,
            "percent": percent,
            "status": status
        })

    return {
        "month": f"{month}-{year}",
        "alerts": alerts
    }
