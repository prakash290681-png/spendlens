# -------------------------------------------------
# Allow HTTP OAuth for LOCAL development
# -------------------------------------------------
import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import datetime
from database import SessionLocal
from models import User
from ingest import ingest_gmail_spends

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
]


# -------------------------------------------------
# Utility: Previous Month Helper
# -------------------------------------------------
def get_previous_month(month_str: str) -> str:
    year, month = map(int, month_str.split("-"))

    if month == 1:
        return f"{year - 1}-12"
    else:
        return f"{year}-{str(month - 1).zfill(2)}"


# -------------------------------------------------
# Login
# -------------------------------------------------
@router.get("/auth/login")
def login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(auth_url)


# -------------------------------------------------
# OAuth Callback
# -------------------------------------------------
@router.get("/auth/callback")
def callback(request: Request):

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    request.session.clear()
    request.session["access_token"] = credentials.token

    token_info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        GOOGLE_CLIENT_ID,
    )

    email = token_info["email"]
    name = token_info.get("name")

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    request.session["user_email"] = user.email

    db.close()

    # ✅ Synchronous ingestion (no background tasks)
    current_month = datetime.utcnow().strftime("%Y-%m")
    previous_month = get_previous_month(current_month)

    ingest_gmail_spends(credentials.token, user.id, current_month)
    ingest_gmail_spends(credentials.token, user.id, previous_month)

    return RedirectResponse("/dashboard")


# -------------------------------------------------
# Logout
# -------------------------------------------------
@router.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


# -------------------------------------------------
# Ingest for selected month (optional manual trigger)
# -------------------------------------------------
@router.post("/ingest/monthly")
def ingest_for_month(request: Request, background_tasks: BackgroundTasks, month: str):

    if "access_token" not in request.session:
        return {"error": "not authenticated"}

    user_id = request.session["user_id"]
    token = request.session["access_token"]

    # 🔥 Always run ingest in background
    background_tasks.add_task(
        ingest_gmail_spends,
        token,
        user_id,
        month,
    )

    return {"status": "started"}
