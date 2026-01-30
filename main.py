from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from datetime import datetime, timezone
from starlette.middleware.sessions import SessionMiddleware
from database import engine, SessionLocal
from models import Base, Transaction
from auth import router as auth_router
from admin import router as admin_router
import os

def get_current_month_range():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    return start, end

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "spendlens-secret"),
    same_site="lax",
    https_only=True
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.include_router(auth_router)
app.include_router(admin_router)

# Create tables if not exist
Base.metadata.create_all(bind=engine)

# Templates
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "templates")
)


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
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


MONTHLY_BUDGETS = {
    "Food Delivery": 2000
}


def evaluate_monthly_budget_alerts(start, end):
    db = SessionLocal()
    alerts = []

    try:
        rows = (
            db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total")
            )
            .filter(
                Transaction.date >= start,
                Transaction.date < end
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

    start, end = get_current_month_range()
    
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

    alerts = evaluate_monthly_budget_alerts(start, end)

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

    start, end = get_current_month_range()

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
