from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func, cast, Date

from database import engine, SessionLocal
from models import Base, Transaction
from auth import router as auth_router
from admin import router as admin_router

#Date Range Helper (Temp: Jan 2026)#
def get_jan_2026_range():
    start = datetime(2026, 1, 1)
    end = datetime(2026, 2, 1)
    return start, end

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "spendlens-secret"),
    same_site="lax",
    https_only=False,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(auth_router)
app.include_router(admin_router)

Base.metadata.create_all(bind=engine)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_current_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


# -------------------------------------------------
# Health
# -------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok"}


# -------------------------------------------------
# Dashboard
# -------------------------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    get_current_user(request)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request},
    )


# -------------------------------------------------
# Monthly Summary (DEDUP AT READ TIME)
# -------------------------------------------------
@app.get("/summary/monthly")
def monthly_summary(request: Request):
    user_id = get_current_user(request)
    start, end = get_jan_2026_range()

    db = SessionLocal()

    category_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category)
        .all()
    )

    merchant_rows = (
        db.query(
            Transaction.merchant,
            func.sum(Transaction.amount).label("total")
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.merchant)
        .all()
    )

    total_spent = sum(r.total for r in category_rows)

    db.close()

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
        "budget_alerts": [],
    }


# -------------------------------------------------
# Monthly Alerts
# -------------------------------------------------
@app.get("/alerts/monthly")
def monthly_alerts(request: Request):
    user_id = get_current_user(request)
    start, end = get_jan_2026_range()

    db = SessionLocal()

    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("spent")
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category)
        .all()
    )

    alerts = []

    MONTHLY_BUDGETS = {
        "Food Delivery": 2000
    }

    for category, spent in rows:
        limit = MONTHLY_BUDGETS.get(category)
        if not limit:
            continue

        percent = round((spent / limit) * 100, 1)
        if percent >= 80:
            alerts.append({
                "category": category,
                "spent": round(spent, 2),
                "limit": limit,
                "percent": percent,
                "status": "exceeded" if percent >= 100 else "warning",
            })
    
    db.close()
    return {"alerts": alerts}

# -------------------------------------------------
# Debug
# -------------------------------------------------
@app.get("/debug/transactions")
def debug_transactions(request: Request, month: str):
    user_id = get_current_user(request)

    year, mon = map(int, month.split("-"))
    start = datetime(year, mon, 1)
    end = datetime(year + (mon == 12), (mon % 12) + 1, 1)

    db = SessionLocal()
    try:
        rows = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= start,
                Transaction.date < end,
            )
            .order_by(Transaction.date)
            .all()
        )

        return [
            {
                "id": r.id,
                "merchant": r.merchant,
                "amount": r.amount,
                "date": r.date.isoformat(),
                "source_id": r.source_id,
            }
            for r in rows
        ]

    finally:
        db.close()
