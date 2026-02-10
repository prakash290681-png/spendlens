from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import Transaction
from spend_extractor import extract_spend
from gmail_service import fetch_recent_emails


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

            # 🔒 enforce ownership
            spend["user_id"] = user_id

            # ✅ DEBUG LOG (correct place)
            print(
                "TRY INSERT:",
                spend["merchant"],
                spend["amount"],
                spend["source_id"],
            )

            try:
                db.add(Transaction(**spend))
                db.commit()
                inserted += 1

            except IntegrityError:
                # duplicate (user_id, source_id)
                db.rollback()
                continue

        print(f"✅ INSERTED {inserted} TRANSACTIONS")

    except Exception as e:
        db.rollback()
        print("❌ INGEST ERROR:", e)

    finally:
        db.close()
