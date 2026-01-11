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
	    Transaction.merchant,
            Transaction.category,
            func.sum(Transaction.amount).label("total")
	).filter(
    	    extract("month", Transaction.date) == current_month,
    	    extract("year", Transaction.date) == current_year
	).group_by(
    	    Transaction.merchant,
    	    Transaction.category
	).all()
    )

    db.close()

    return {
        "month": f"{month}-{year}",
        "summary": [
            {"merchant": r.merchant,
             "category": r.category,
             "total": r.total
	    } 
	    for r in results
        ]
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )
