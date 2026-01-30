from database import SessionLocal
from models import Transaction
from spend_extractor import extract_spend
from gmail_service import fetch_recent_emails


def ingest_gmail_spends(access_token: str, user_id: int):
    emails, service = fetch_recent_emails(access_token, return_service=True)

    db = SessionLocal()
    inserted = 0

    try:
        for email in emails:
            spend = extract_spend(email, service)
            if not spend:
                continue

            # 🔁 prevent duplicates
            exists = db.query(Transaction).filter(
                Transaction.source_id == spend["source_id"],
                Transaction.user_id == user_id
            ).first()

            if exists:
                continue

            existing = (
                db.query(Transaction)
                .filter(Transaction.source_id == spend["source_id"])
                .first()
            )

            if existing:
                continue  # already ingested, skip safely

            tx = Transaction(
                user_id=user_id,
                merchant=spend["merchant"],
                category=spend["category"],
                amount=spend["amount"],
                date=spend["date"],
                source_id=spend["source_id"],
            )

            db.add(tx)

            inserted += 1

        db.commit()
        print(f"✅ Inserted {inserted} transactions")

    finally:
        db.close()
