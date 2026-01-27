from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os
from datetime import timezone

from gmail_service import fetch_recent_emails
from spend_extractor import extract_spend
from database import SessionLocal
from models import Transaction
from date_utils import normalize_date
from sqlalchemy import Date


router = APIRouter()

TARGET_YEAR = 2026
TARGET_MONTH = 1

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
    flow = create_flow()
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
def callback(request: Request):
    flow = create_flow()
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials

    emails, service = fetch_recent_emails(
        creds.token,
        return_service=True
    )

    db = SessionLocal()
    inserted = 0

    try:
        for email in emails:
            # ---------- HARD DATE FILTER ----------
            email_date = normalize_date(email.get("Date"))
            if not email_date:
                continue

            email_date = email_date.astimezone(timezone.utc)

            if (
                email_date.year != TARGET_YEAR
                or email_date.month != TARGET_MONTH
            ):
                print(">>> SKIP EMAIL BEFORE PARSING:", email_date)
                continue

            # ---------- PARSE ----------
            spend = extract_spend(email, service)
            print("DEBUG spend:", spend)

            if spend is None:
                print(">>> SKIP: spend extraction failed")
                continue

            if spend.get("amount") is None or spend["amount"] <= 0:
                print(">>> SKIP: invalid amount")
                continue

            if spend.get("merchant") == "Unknown":
                print(">>> SKIP: unknown merchant")
                continue

            # --- DUPLICATE CHECK ---

            if spend["merchant"] == "Swiggy":
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.merchant == "Swiggy",
                        Transaction.date.cast(Date) == spend["date"].date()
                    )
                    .first()
                )

                if existing:
                    print(">>> SWIGGY DUPLICATE (date-level) — SKIPPING:", spend)
                    continue
            else:
                existing = (
                    db.query(Transaction)
                    .filter(Transaction.source_id == spend["source_id"])
                    .first()
                )

                if existing:
                    print(">>> DUPLICATE TRANSACTION — SKIPPING:", spend["source_id"])
                    continue


            # ---------- INSERT ----------
            tx = Transaction(**spend)
            try:
                db.add(tx)
                db.commit()
                inserted += 1
            except Exception as e:
                print("DB ERROR:", e)
                db.rollback()

    finally:
        db.close()

    print("TOTAL INSERTED:", inserted)
    return RedirectResponse("/dashboard")
