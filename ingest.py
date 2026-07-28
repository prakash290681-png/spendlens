from datetime import timedelta
import traceback

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

            try:
                print("FETCHED SUBJECT:", email["Subject"])

                spend = extract_spend(email, service)
                print("RETURNED FROM PARSER:", spend)

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
                # 2️⃣ SOFT DUPLICATE
                # =====================================================
                similar = (
                    db.query(Transaction)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.amount == spend["amount"],
                        Transaction.date >= spend["date"] - timedelta(hours=6),
                        Transaction.date <= spend["date"] + timedelta(hours=6),
                    )
                    .first()
                )

                if similar:
                    print("⛔ SKIP possible duplicate:", spend)
                    continue

                # =====================================================
                # INSERT
                # =====================================================
                db.add(Transaction(**spend))
                db.commit()
                inserted += 1

            except Exception:
                db.rollback()

                print("\n" + "=" * 80)
                print("❌ ERROR PROCESSING EMAIL")
                print("SUBJECT:", email.get("Subject"))
                print("MESSAGE ID:", email.get("id"))
                traceback.print_exc()
                print("=" * 80 + "\n")

                # Continue with next email
                continue

        print(f"✅ INSERTED {inserted} TRANSACTIONS")

    except Exception:
        db.rollback()

        print("\n" + "=" * 80)
        print("❌ INGESTION FAILED")
        traceback.print_exc()
        print("=" * 80 + "\n")

    finally:
        db.close()