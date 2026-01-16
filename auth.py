import os
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from gmail_service import fetch_recent_emails
from email_filter import is_order_email
from spend_extractor import extract_spend
from database import SessionLocal
from models import Transaction

router = APIRouter()

# Allow HTTP for local dev only
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def create_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
            }
        },
        scopes=SCOPES,
    )


@router.get("/auth/login")
def login():
    print(">>> AUTH LOGIN HIT <<<")
    flow = create_flow()
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
def callback(request: Request):
    print(">>> AUTH LOGIN HIT <<<")

    flow = create_flow()
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials

    emails = fetch_recent_emails(creds.token, max_results=30)
    order_emails = [e for e in emails if is_order_email(e)]
    spends = [extract_spend(email) for email in order_emails]

    db = SessionLocal()
    inserted = 0

    for spend in spends:
        print("RAW SPEND:", spend)

        if spend["amount"] is None or spend["date"] is None:
            print(">>> SKIP: invalid spend")
            continue

        tx = Transaction(
            merchant=spend["merchant"],
            category=spend["category"],
            amount=spend["amount"],
            date=spend["date"],
            source_id=spend["source_id"]
        )

        try:
            db.add(tx)
            db.commit()
            inserted += 1
            print(">>> INSERTED:", spend["source_id"])
        except IntegrityError:
            db.rollback()
        print(">>> DUPLICATE SKIPPED:", spend["source_id"])
 
       20
# ✅ THESE MUST BE OUTSIDE THE LOOP
db.commit()
print("TOTAL INSERTED:", inserted)
db.close()

return RedirectResponse(url="/dashboard")

