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
# OAuth Callback (CORRECT & SAFE)
# -------------------------------------------------
@router.get("/auth/callback")
def callback(request: Request, background_tasks: BackgroundTasks):
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

    # 1️⃣ Exchange code → tokens
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    # 2️⃣ Verify identity
    token_info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=30, # required for local dev
    )


    email = token_info["email"]
    name = token_info.get("name")

    # 3️⃣ User upsert
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4️⃣ Session MUST be set BEFORE ingest
    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["ingesting"] = True

    db.close()

    # 5️⃣ Run ingest in BACKGROUND (no DB lock)
    background_tasks.add_task(
        ingest_gmail_spends,
        credentials.token,
        user.id,
    )

    return RedirectResponse("/dashboard")


# -------------------------------------------------
# Logout
# -------------------------------------------------
@router.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
