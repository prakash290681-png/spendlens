from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from database import SessionLocal
from models import Transaction
from spend_extractor import extract_spend
from gmail_service import fetch_recent_emails
from datetime import timedelta


def ingest_gmail_spends(access_token: str, user_id: int, month: str):
    print("🚀 INGEST STARTED FOR USER:", user_id, "MONTH:", month)

    emails, service = fetch_recent_emails(
        access_token,
        month,
        return_service=True
    )

    db = SessionLocal()
    inserted = 0

    try:
        for email in emails:

            spend = extract_spend(email, service)
            if not spend:
                continue

            spend["user_id"] = user_id

            print(
                "TRY INSERT:",
                spend["merchant"],
                spend["amount"],
                spend["source_id"],
            )

            # -------------------------------------------------
            # 1️⃣ Prevent duplicate by source_id
            # -------------------------------------------------
            existing_by_source = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.source_id == spend["source_id"]
            ).first()

            if existing_by_source:
                print("⏭ Skipped (duplicate source_id)")
                continue

            # -------------------------------------------------
            # 2️⃣ Prevent logical duplicate
            # Same merchant + same amount + within 2 hours
            # -------------------------------------------------
            window_start = spend["date"] - timedelta(hours=2)
            window_end = spend["date"] + timedelta(hours=2)

            existing_similar = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.merchant == spend["merchant"],
                Transaction.amount == spend["amount"],
                Transaction.date >= window_start,
                Transaction.date <= window_end,
            ).first()

            if existing_similar:
                print("⏭ Skipped (logical duplicate)")
                continue

            # -------------------------------------------------
            # 3️⃣ Insert
            # -------------------------------------------------
            try:
                db.add(Transaction(**spend))
                db.commit()
                inserted += 1

            except IntegrityError:
                db.rollback()
                continue

        print(f"✅ INSERTED {inserted} TRANSACTIONS")

    except Exception as e:
        db.rollback()
        print("❌ INGEST ERROR:", e)

    finally:
        db.close()
