from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime

from auth import router
from database import engine, SessionLocal
from models import Base, Transaction, Budget
from pydantic import BaseModel

app = FastAPI()
app.include_router(router)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# -------------------- BUDGET APIs --------------------

class BudgetIn(BaseModel):
    category: str
    monthly_limit: int


@app.post("/budget")
def set_budget(budget: BudgetIn, db: Session = Depends(get_db)):
    existing = db.query(Budget).filter(
        Budget.category == budget.category
    ).first()

    if existing:
        existing.monthly_limit = budget.monthly_limit
    else:
        db.add(
            Budget(
                category=budget.category,
                monthly_limit=budget.monthly_limit
            )
        )

    db.commit()
    return budget


@app.get("/budget/alerts")
def budget_alerts(db: Session = Depends(get_db)):
    month = datetime.now().month
    year = datetime.now().year

    spends = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total_spent")
        )
        .filter(
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year
        )
        .group_by(Transaction.category)
        .all()
    )

    budgets = {
        b.category: b.monthly_limit
        for b in db.query(Budget).all()
    }

    alerts = []

    for s in spends:
        limit = budgets.get(s.category)
        if limit and s.total_spent >= limit:
            alerts.append({
                "category": s.category,
                "spent": s.total_spent,
                "limit": limit,
                "exceeded_by": s.total_spent - limit
            })

    return {
        "month": f"{month}-{year}",
        "alerts": alerts
    }
