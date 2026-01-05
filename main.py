from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from auth import router
from database import engine, SessionLocal
from models import Base, Transaction
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

app = FastAPI()
app.include_router(router)

templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

@app.get("/")
def health():
    return {"status": "SpendLens backend running"}

@app.get("/summary/monthly")
def monthly_summary():
    db: Session = SessionLocal()

    month = datetime.now().month
    year = datetime.now().year

    results = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount)
        )
        .filter(extract("month", Transaction.date) == month)
        .filter(extract("year", Transaction.date) == year)
        .group_by(Transaction.category)
        .all()
    )

    db.close()

    return {
        "month": f"{month}-{year}",
        "summary": [
            {"category": r[0], "total": r[1]} for r in results
        ]
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )
import os

if os.getenv("RENDER") == "true":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
