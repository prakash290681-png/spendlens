from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
load_dotenv()
import os
print("CLIENT_ID:", os.getenv("GOOGLE_CLIENT_ID"))
print("REDIRECT:", os.getenv("GOOGLE_REDIRECT_URI"))
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi import Request
from auth import router as auth_router
from database import engine
from models import Base

app = FastAPI()
Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)

@app.get("/")
def health_check():
    return {"status": "SpendLens backend is running 🚀"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

