from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from datetime import datetime, timezone

from database import engine, SessionLocal
from models import Base, Transaction
from auth import router as auth_router
from admin import router as admin_router

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()

app.include_router(auth_router)
app.include_router(admin_router)

# Create tables if not exist
Base.metadata.create_all(bind=engine)

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/admin/debug-zomato")
def debug_zomato_rows():
    db = SessionLocal()

    rows = (
        db.query(Transaction)
        .filter(Transaction.merchant == "Zomato")
        .all()
    )

    db.close()

    return [
        {
            "id": r.id,
            "amount": r.amount,
            "date": r.date.isoformat(),
            "source_id": r.source_id,
        }
        for r in rows
    ]

# -------------------------------------------------
# Health check
# -------------------------------------------------
@app.get("/")
def health_check():
    return {"status": "SpendLens backend is running 🚀"}

# -------------------------------------------------
# Dashboard
# -------------------------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    print("🔥🔥🔥 DASHBOARD ROUTE HIT 🔥🔥🔥")
    print("🔥 templates dir =", templates.directory)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

# -------------------------------------------------
# Monthly config
# -------------------------------------------------
TARGET_YEAR = 2026
TARGET_MONTH = 1

MONTHLY_BUDGETS = {
    "Food Delivery": 2000
}


def evaluate_monthly_budget_alerts(year: int, month: int):
    db = SessionLocal()
    alerts = []

    try:
        rows = (
            db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total")
            )
            .filter(
                func.extract("year", Transaction.date) == year,
                func.extract("month", Transaction.date) == month,
            )
            .group_by(Transaction.category)
            .all()
        )

        for category, total in rows:
            budget = MONTHLY_BUDGETS.get(category)

            if budget and total > budget:
                alerts.append({
                    "category": category,
                    "spent": round(float(total), 2),
                    "budget": budget,
                    "exceeded_by": round(float(total - budget), 2)
                })

        return alerts

    finally:
        db.close()

# -------------------------------------------------
# Monthly summary
# -------------------------------------------------
@app.get("/summary/monthly")
def monthly_summary():
    db = SessionLocal()

    start = datetime(TARGET_YEAR, TARGET_MONTH, 1, tzinfo=timezone.utc)
    end = (
        datetime(TARGET_YEAR + 1, 1, 1, tzinfo=timezone.utc)
        if TARGET_MONTH == 12
        else datetime(TARGET_YEAR, TARGET_MONTH + 1, 1, tzinfo=timezone.utc)
    )

    category_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category)
        .all()
    )

    merchant_rows = (
        db.query(
            Transaction.merchant,
            func.sum(Transaction.amount).label("total")
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.merchant)
        .all()
    )

    total_spent = sum(row.total for row in category_rows)

    db.close()

    alerts = evaluate_monthly_budget_alerts(
    year=TARGET_YEAR,
    month=TARGET_MONTH
)

    return {
        "total_spent": round(total_spent, 2),
        "by_category": [
            {"category": r.category, "total": round(r.total, 2)}
            for r in category_rows
        ],
        "by_merchant": [
            {"merchant": r.merchant, "total": round(r.total, 2)}
            for r in merchant_rows
        ],
        "budget_alerts": alerts  
    }

# -------------------------------------------------
# Monthly alerts
# -------------------------------------------------
@app.get("/alerts/monthly")
def monthly_alerts():
    db = SessionLocal()

    start = datetime(TARGET_YEAR, TARGET_MONTH, 1, tzinfo=timezone.utc)
    end = (
        datetime(TARGET_YEAR + 1, 1, 1, tzinfo=timezone.utc)
        if TARGET_MONTH == 12
        else datetime(TARGET_YEAR, TARGET_MONTH + 1, 1, tzinfo=timezone.utc)
    )

    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("spent")
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category)
        .all()
    )

    alerts = []

    for row in rows:
        limit = MONTHLY_BUDGETS.get(row.category)
        if not limit:
            continue

        percent = round((row.spent / limit) * 100, 1)

        if percent >= 80:
            alerts.append({
                "category": row.category,
                "spent": round(row.spent, 2),
                "limit": limit,
                "percent": percent,
                "status": "exceeded" if percent >= 100 else "warning"
            })

    db.close()

    return {"alerts": alerts}
