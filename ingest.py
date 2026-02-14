from datetime import timedelta
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
            print("FETCHED SUBJECT:", email["Subject"])
            
            spend = extract_spend(email, service)
            if not spend:
                continue

            spend["user_id"] = user_id

            # 🔥 STRONG DUPLICATE CHECK
            # 1️⃣ absolute protection – same email
            existing = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.source_id == spend["source_id"],
                )
                .first()
            )

            if existing:
                print("⛔ SKIP source duplicate:", spend["source_id"])
                continue


            # 2️⃣ fallback fuzzy match
            existing = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.merchant == spend["merchant"],
                    Transaction.amount == spend["amount"],
                    Transaction.date >= spend["date"] - timedelta(hours=8),
                    Transaction.date <= spend["date"] + timedelta(hours=8),
                )
                .first()
            )

            if existing:
                print("⛔ SKIP fuzzy duplicate:", spend)
                continue

            db.add(Transaction(**spend))
            db.commit()
            inserted += 1

        print(f"✅ INSERTED {inserted} TRANSACTIONS")

    except Exception as e:
        db.rollback()
        print("❌ INGEST ERROR:", e)

    finally:
        db.close()
