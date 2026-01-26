from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import router as auth_router
from database import engine, SessionLocal
from models import Base, Transaction

MONTHLY_BUDGETS = {
    "Food Delivery": 2000
}

# --- App setup ---
app = FastAPI()

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Templates
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(auth_router)

# --- Health check ---
@app.get("/")
def health_check():
    return {"status": "SpendLens backend is running 🚀"}

# --- Dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

# --- Monthly summary ---
from datetime import datetime, timezone

TARGET_YEAR = 2026
TARGET_MONTH = 1

MONTHLY_BUDGETS = {
    "Food Delivery": 2000
}


# --- Monthly summary ---
@app.get("/summary/monthly")
def monthly_summary():
    db = SessionLocal()

    start = datetime(TARGET_YEAR, TARGET_MONTH, 1, tzinfo=timezone.utc)
    if TARGET_MONTH == 12:
        end = datetime(TARGET_YEAR + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(TARGET_YEAR, TARGET_MONTH + 1, 1, tzinfo=timezone.utc)

    # Category breakdown
    category_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category)
        .all()
    )

    # Merchant breakdown
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

    by_category = [
        {"category": row.category, "total": round(row.total, 2)}
        for row in category_rows
    ]

    by_merchant = [
        {"merchant": row.merchant, "total": round(row.total, 2)}
        for row in merchant_rows
    ]

    db.close()

    return {
        "total_spent": round(total_spent, 2),
        "by_category": by_category,
        "by_merchant": by_merchant
    }


# --- Monthly alerts ---
@app.get("/alerts/monthly")
def monthly_alerts():
    db = SessionLocal()

    start = datetime(TARGET_YEAR, TARGET_MONTH, 1, tzinfo=timezone.utc)
    if TARGET_MONTH == 12:
        end = datetime(TARGET_YEAR + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(TARGET_YEAR, TARGET_MONTH + 1, 1, tzinfo=timezone.utc)

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

    # --- Merchant breakdown ---
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

    by_category = [
        {"category": row.category, "total": round(row.total, 2)}
        for row in category_rows
    ]

    by_merchant = [
        {"merchant": row.merchant, "total": round(row.total, 2)}
        for row in merchant_rows
    ]

    db.close()

    return {
        "total_spent": round(total_spent, 2),
        "by_category": by_category,
        "by_merchant": by_merchant
    }
