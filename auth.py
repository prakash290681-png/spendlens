from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os
from datetime import timezone

from gmail_service import fetch_recent_emails
from spend_extractor import extract_spend
from database import SessionLocal
from models import Transaction
from date_utils import normalize_date

from sqlalchemy import Date   # ✅ MISSING IMPORT (IMPORTANT)

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
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
def callback(request: Request):
    print("🔥 RUNNING AUTH.PY VERSION 2026-01-FINAL-STABLE")

    flow = create_flow()
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials

    emails, service = fetch_recent_emails(
        creds.token,
        return_service=True,
    )

    db = SessionLocal()
    inserted = 0

    try:
        for email in emails:

            # ---------- DATE FILTER ----------
            email_date = normalize_date(email.get("Date"))
            if not email_date:
                continue

            email_date = email_date.astimezone(timezone.utc)
            if email_date.year != TARGET_YEAR or email_date.month != TARGET_MONTH:
                continue

            # ---------- EXTRACT ----------
            spend = extract_spend(email, service)
            # 🚫 BLOCK Swiggy bank alerts if order email exists
            if spend and spend["merchant"] == "Swiggy" and spend.get("source") == "bank_alert":
                existing_email = (
                    db.query(Transaction)
                    .filter(
                        Transaction.merchant == "Swiggy",
                        Transaction.amount == spend["amount"],
                        Transaction.date.cast(Date) == spend["date"].date(),
                    )
                    .first()
                )

                if existing_email:
                    print("🚫 SKIPPING Swiggy bank alert (order email already exists)")
                    continue

            print("DEBUG spend:", spend)

            if not spend or spend.get("amount") is None or spend["amount"] <= 0:
                continue

            # ---------- NORMALIZE DATE (DAY LEVEL) ----------
            spend["date"] = (
                spend["date"]
                .astimezone(timezone.utc)
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )

            # =====================================================
            # ✅ FINAL, CORRECT DEDUPE LOGIC
            # =====================================================

            if spend["merchant"] == "Swiggy":

                # 1️⃣ Bank alert should NEVER duplicate a Swiggy order email
                if spend.get("source") == "bank_alert":
                    existing_order = (
                        db.query(Transaction)
                        .filter(
                            Transaction.merchant == "Swiggy",
                            Transaction.amount == spend["amount"],
                            Transaction.date.cast(Date) == spend["date"].date(),
                            Transaction.source == "swiggy_email",
                        )
                        .first()
                    )

                    if existing_order:
                        print(
                            ">>> BANK ALERT SKIPPED (order email exists):",
                            spend,
                        )
                        continue

                # 2️⃣ Absolute safety: only ONE Swiggy row per (date + amount)
                existing = (
                    db.query(Transaction)
                    .filter(
                        Transaction.merchant == "Swiggy",
                        Transaction.amount == spend["amount"],
                        Transaction.date.cast(Date) == spend["date"].date(),
                    )
                    .first()
                )

                if existing:
                    print(">>> DUPLICATE SWIGGY — SKIPPING:", spend)
                    continue

            else:
                # ---------- NON-SWIGGY ----------
                if spend.get("source_id"):
                    existing = (
                        db.query(Transaction)
                        .filter(Transaction.source_id == spend["source_id"])
                        .first()
                    )
                    if existing:
                        print(
                            ">>> DUPLICATE SOURCE_ID — SKIPPING:",
                            spend["source_id"],
                        )
                        continue

            # ---------- INSERT ----------
            try:
                db.add(Transaction(**spend))
                db.commit()
                inserted += 1
            except Exception as e:
                print("DB ERROR:", e)
                db.rollback()

    finally:
        db.close()

    print("TOTAL INSERTED:", inserted)
    return RedirectResponse("/dashboard")
# =====================================================
# 🔥 ONE-TIME CLEANUP — REMOVE EXISTING SWIGGY DUPLICATES
# =====================================================
from sqlalchemy import Date

@router.post("/admin/cleanup-swiggy")
def cleanup_swiggy():
    db = SessionLocal()

    rows = (
        db.query(Transaction)
        .filter(Transaction.merchant == "Swiggy")
        .order_by(Transaction.date)
        .all()
    )

    seen = set()
    deleted = 0

    for row in rows:
        key = (row.amount, row.date.date())

        if key in seen:
            db.delete(row)
            deleted += 1
        else:
            seen.add(key)

    db.commit()
    db.close()

    return {"deleted_duplicates": deleted}

