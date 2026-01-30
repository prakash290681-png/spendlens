from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
import time
import base64

# >>> ADDED
from database import SessionLocal
from models import Transaction
from spend_extractor import extract_spend


def gmail_timestamp(dt: datetime) -> int:
    return int(time.mktime(dt.timetuple()))


# -------------------------------------------------
# BODY EXTRACTION — FIXED (HTML + TEXT + NESTED)
# -------------------------------------------------
def extract_body(payload):
    body = payload.get("body", {}).get("data")
    if body:
        return base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")

    def walk_parts(parts):
        for part in parts:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")

            if mime in ("text/plain", "text/html") and data:
                return base64.urlsafe_b64decode(
                    data
                ).decode("utf-8", errors="ignore")

            if "parts" in part:
                found = walk_parts(part["parts"])
                if found:
                    return found
        return ""

    if "parts" in payload:
        return walk_parts(payload["parts"])

    return ""


# -------------------------------------------------
# ATTACHMENTS
# -------------------------------------------------
def extract_attachments(payload):
    attachments = []

    if "parts" not in payload:
        return attachments

    for part in payload["parts"]:
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            attachments.append({
                "filename": part["filename"],
                "attachmentId": part["body"]["attachmentId"],
                "mimeType": part.get("mimeType"),
            })

    return attachments


# -------------------------------------------------
# FETCH EMAILS + PERSIST SPENDS
# -------------------------------------------------
def fetch_recent_emails(access_token: str, return_service=False):
    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)

    START = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    END   = int(datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp())

    query = (
        '('
        'subject:"Zomato" OR '
        'from:swiggy OR '
        'from:hdfc OR '
        'from:icici OR '
        'from:axis OR '
        'from:sbi'
        ') '
        f'after:{START} before:{END}'
    )

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=500
    ).execute()

    messages = results.get("messages", [])
    emails = []

    db = SessionLocal()  # >>> ADDED

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        email = {h["name"]: h["value"] for h in headers}

        email["id"] = msg["id"]
        email["Body"] = extract_body(msg_data["payload"])
        email["snippet"] = msg_data.get("snippet", "")
        email["labelIds"] = msg_data.get("labelIds", [])
        email["attachments"] = extract_attachments(msg_data["payload"])

        emails.append(email)

        # -------------------------------------------------
        # >>> PERSIST TRANSACTION (NEW)
        # -------------------------------------------------
        spend = extract_spend(email, service)

        if spend:
            exists = (
                db.query(Transaction)
                .filter(Transaction.source_id == spend["source_id"])
                .first()
            )

            if not exists:
                txn = Transaction(
                    merchant=spend["merchant"],
                    category=spend["category"],
                    amount=spend["amount"],
                    date=spend["date"],
                    source_id=spend["source_id"],
                )
                db.add(txn)
                db.commit()

    db.close()

    if return_service:
        return emails, service

    return emails
