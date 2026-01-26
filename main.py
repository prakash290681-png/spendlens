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
@app.get("/summary/monthly")
def monthly_summary():
    db: Session = SessionLocal()

    total = db.query(func.sum(Transaction.amount)).scalar() or 0

    by_category = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total")
        )
        .group_by(Transaction.category)
        .all()
    )

    db.close()

    return {
        "total_spent": round(float(total), 2),
        "by_category": [
            {
                "category": row.category,
                "total": round(float(row.total), 2)
            }
            for row in by_category
        ]
    }
