from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timezone
from calendar import monthrange
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func

from database import engine, SessionLocal
from models import Base, Transaction
from auth import router as auth_router
from admin import router as admin_router

# -------------------------------------------------
# Date Helpers
# -------------------------------------------------
from datetime import datetime
from calendar import monthrange


def get_month_range(month: str | None):
    if month:
        year, mon = map(int, month.split("-"))
    else:
        today = datetime.utcnow()
        year, mon = today.year, today.month

    start = datetime(year, mon, 1, tzinfo=timezone.utc)

    if mon == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, mon + 1, 1, tzinfo=timezone.utc)

    return start, end

def get_previous_month(month_str: str | None):
    if month_str:
        year, mon = map(int, month_str.split("-"))
    else:
        today = datetime.utcnow()
        year, mon = today.year, today.month

    if mon == 1:
        return f"{year-1}-12"
    return f"{year}-{str(mon-1).zfill(2)}"



# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()

from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(BASE_DIR, "static")

if os.path.isdir(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    print("✅ Static directory mounted:", static_path)
else:
    print("⚠️ Static directory missing:", static_path)


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

@app.get("/system/ready")
def system_ready():
    # simplest version: always ready
    # later you can wire this to ingestion status
    return {"ready": True}


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
# Monthly Summary
# -------------------------------------------------
@app.get("/summary/monthly")
def monthly_summary(request: Request, month: str | None = None):
    user_id = get_current_user(request)

    start, end = get_month_range(month)

    prev_month = get_previous_month(month)
    p_start, p_end = get_month_range(prev_month)

    db = SessionLocal()

    # ---- Current month ----
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

    # ---- Previous month ----
    prev_total_row = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= p_start,
            Transaction.date < p_end,
        )
        .scalar()
    )

    previous_total = prev_total_row or 0

    # ---- Change ----
    change_percent = 0
    if previous_total > 0:
        change_percent = round(
            ((total_spent - previous_total) / previous_total) * 100, 1
        )

    db.close()

    print("DEBUG MONTH:", month)
    print("DEBUG RANGE:", start, end)
    print("DEBUG TOTAL:", total_spent)

    row_users = {user_id}
    print("AUTH USER:", user_id)
    print("RETURNING DATA FOR:", row_users)

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
        "comparison": {
            "previous_total": round(previous_total, 2),
            "change_percent": change_percent,
            "trend": "up" if change_percent > 0 else "down" if change_percent < 0 else "same"
        },
        "budget_alerts": [],
    }


# -------------------------------------------------
# Monthly Alerts
# -------------------------------------------------
@app.get("/alerts/monthly")
def monthly_alerts(request: Request, month: str | None = None):
    user_id = get_current_user(request)
    start, end = get_month_range(month)

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
                "over_by": round(percent - 100, 1) if percent >= 100 else 0,
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


# -------------------------------------------------
# Recurring Merchants
# -------------------------------------------------
@app.get("/insights/recurring")
def recurring_merchants(request: Request):
    user_id = get_current_user(request)

    db = SessionLocal()

    rows = (
        db.query(
            Transaction.merchant,
            func.count(func.strftime("%Y-%m", Transaction.date)).label("months"),
            func.max(Transaction.date).label("last_date")
        )
        .filter(Transaction.user_id == user_id)
        .group_by(Transaction.merchant)
        .having(func.count(func.strftime("%Y-%m", Transaction.date)) >= 2)
        .order_by(func.count(func.strftime("%Y-%m", Transaction.date)).desc())
        .all()
    )

    results = []

    for merchant, months, last_date in rows:
        last_amount = (
            db.query(Transaction.amount)
            .filter(
                Transaction.user_id == user_id,
                Transaction.merchant == merchant,
                Transaction.date == last_date
            )
            .scalar()
        )

        results.append({
            "merchant": merchant,
            "months": months,
            "last_amount": last_amount
        })

    db.close()
    return results

# -------------------------------------------------
# AI Insights (rule-based intelligence)
# -------------------------------------------------
@app.get("/insights/ai")
def ai_insights(request: Request, month: str | None = None):
    user_id = get_current_user(request)

    start, end = get_month_range(month)
    prev_month = get_previous_month(month)
    p_start, p_end = get_month_range(prev_month)

    db = SessionLocal()

    insights = []

    # ---- totals ----
    current_total = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .scalar()
    ) or 0

    previous_total = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= p_start,
            Transaction.date < p_end,
        )
        .scalar()
    ) or 0

    # ---- month-end prediction ----
    today = datetime.today()

    # only predict if viewing current month
    if start.year == today.year and start.month == today.month:
        days_passed = today.day
        if days_passed > 0:
            avg_per_day = current_total / days_passed

            # total days in this month
            last_day = (end - start).days

            projected_total = round(avg_per_day * last_day, 2)

            insights.append(
                f"At this pace, you may spend about ₹{projected_total} by month end."
            )

    if previous_total > 0:
        change = round(((current_total - previous_total) / previous_total) * 100, 1)
        if change > 0:
            insights.append(f"Spending increased {change}% compared to last month.")
        elif change < 0:
            insights.append(f"Good job! Spending dropped {abs(change)}% from last month.")

    # ---- top category ----
    top_category = (
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
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )

    if top_category:
        insights.append(f"{top_category[0]} is your top spending category.")

    # ---- top merchant ----
    top_merchant = (
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
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )

    if top_merchant:
        insights.append(f"{top_merchant[0]} is your highest expense merchant.")

    # ---- recurring ----
    recurring_count = (
        db.query(Transaction.merchant)
        .filter(Transaction.user_id == user_id)
        .group_by(Transaction.merchant)
        .having(func.count(func.strftime("%Y-%m", Transaction.date)) >= 2)
        .count()
    )

    if recurring_count:
        insights.append(f"You have {recurring_count} recurring merchants.")

    db.close()

    return insights
# ---------------------------
# TEMPORARY DB RESET ROUTE
# ---------------------------
from database import SessionLocal
from models import Transaction

@app.get("/wipe")
def wipe(request: Request):
    user_id = get_current_user(request)  # must be logged in

    db = SessionLocal()
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.commit()
    db.close()

    return {"status": "your transactions deleted"}

@app.get("/delete_tx/{source_id}")
def delete_tx(source_id: str):
    db = SessionLocal()
    db.query(Transaction).filter(Transaction.source_id == source_id).delete()
    db.commit()
    db.close()
    return {"deleted": source_id}
