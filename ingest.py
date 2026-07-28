from datetime import timedelta
import traceback

from database import SessionLocal
from models import Transaction
from spend_extractor import extract_spend
from gmail_service import fetch_recent_emails


def ingest_gmail_spends(access_token: str, user_id: int, month: str):
    print(f"🚀 Starting Gmail ingestion | User: {user_id} | Month: {month}")

    emails, service = fetch_recent_emails(
        access_token,
        month,
        return_service=True
    )
    print(f"📧 Retrieved {len(emails)} email(s) from Gmail.")
    
    db = SessionLocal()
    inserted = 0

    try:
        for email in emails:

            try:
                
                spend = extract_spend(email, service)

                if not spend:
                    print(f"⚠️ Skipped email (no spend detected): {email.get('Subject', 'No Subject')}")
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
                    print(f"⏭️ Skipped duplicate Gmail message: {spend['source_id']}")
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
                    print(
                        f"⏭️ Skipped possible duplicate | "
                        f"{spend['merchant']} | ₹{spend['amount']} | {spend['date']}"
)
                    continue

                # =====================================================
                # INSERT
                # =====================================================
                db.add(Transaction(**spend))
                db.commit()
                inserted += 1

            except Exception:
                db.rollback()

                print("❌ Error processing email")
                print(f"Subject   : {email.get('Subject', 'Unknown')}")
                print(f"Message ID: {email.get('id', 'Unknown')}")
                traceback.print_exc()

                # Continue with next email
                continue

        print(f"✅ Gmail ingestion completed. Inserted {inserted} new transactions.")

    except Exception:
        db.rollback()

        print("❌ Gmail ingestion failed.")
        traceback.print_exc()

    finally:
        db.close()