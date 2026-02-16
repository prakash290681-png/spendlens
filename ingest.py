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
                print("❌ SKIPPED BY EXTRACTOR:", email["Subject"])
                continue

            spend["user_id"] = user_id

            # =====================================================
            # 1️⃣ HARD DUPLICATE → SAME GMAIL MESSAGE
            # =====================================================
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


            # =====================================================
            # 2️⃣ SOFT DUPLICATE → ONLY WARN, DO NOT BLOCK
            # =====================================================
            similar = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.amount == spend["amount"],
                    Transaction.date >= spend["date"] - timedelta(minutes=60),
                    Transaction.date <= spend["date"] + timedelta(minutes=60),

                )
                .first()
            )

            if similar:
                print("⛔ SKIP cross-source duplicate:", spend)
                continue



            # =====================================================
            # INSERT
            # =====================================================
            db.add(Transaction(**spend))
            db.commit()
            inserted += 1

        print(f"✅ INSERTED {inserted} TRANSACTIONS")

    except Exception as e:
        db.rollback()
        print("❌ INGEST ERROR:", e)

    finally:
        db.close()
