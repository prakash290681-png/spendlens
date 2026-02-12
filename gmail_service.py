from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
from calendar import monthrange
import time
import base64


def gmail_timestamp(dt: datetime) -> int:
    return int(time.mktime(dt.timetuple()))


# -------------------------------------------------
# BODY EXTRACTION
# -------------------------------------------------
def extract_body(payload):
    body = payload.get("body", {}).get("data")
    if body:
        return base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")

    text_plain = None
    text_html = None

    def walk(parts):
        nonlocal text_plain, text_html
        for part in parts:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")

            if data:
                decoded = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="ignore"
                )
                if mime == "text/plain" and not text_plain:
                    text_plain = decoded
                elif mime == "text/html" and not text_html:
                    text_html = decoded

            if "parts" in part:
                walk(part["parts"])

    walk(payload.get("parts", []))

    return text_plain or text_html or ""


# -------------------------------------------------
# ATTACHMENTS
# -------------------------------------------------
def extract_attachments(payload):
    attachments = []
    for part in payload.get("parts", []):
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            attachments.append({
                "filename": part["filename"],
                "attachmentId": part["body"]["attachmentId"],
                "mimeType": part.get("mimeType"),
            })
    return attachments


# -------------------------------------------------
# FETCH EMAILS ONLY (NO DB)
# -------------------------------------------------
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_email_content(service, message_id):
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    print("📩 MSG ID:", msg["id"])
    print("📩 PAYLOAD MIME:", msg["payload"].get("mimeType"))
    print("📩 HAS PARTS:", "parts" in msg["payload"])
    print(
        "📩 PART MIMES:",
        [p.get("mimeType") for p in msg["payload"].get("parts", [])]
    )

    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = extract_body(msg["payload"])

    print("🧪 BODY LEN:", len(body))
    print("🧪 BODY SAMPLE:", body[:200].replace("\n", " "))

    return {
        "id": msg["id"],
        "From": headers.get("From", ""),
        "Subject": headers.get("Subject", ""),
        "Date": headers.get("Date", ""),
        "Body": body,  # body parsing already handled elsewhere in your codebase
    }


def fetch_recent_emails(access_token: str, month: str, return_service=False):
    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)

    year, mon = map(int, month.split("-"))

    start = f"{year}/{mon:02d}/01"
    end = f"{year}/{mon:02d}/{monthrange(year, mon)[1]}"

    query = (
        '('
        'subject:Swiggy OR '
        'from:swiggy OR '
        'instamart OR '
        '"order delivered" OR '
        '"order placed" OR '
        'subject:Zomato OR '
        'from:zomato OR '
        'from:hdfc OR from:icici OR from:axis OR from:sbi'
        ') '
        f'after:{start} before:{end}'
    )
    print("QUERY:", query)
    print("EMAIL COUNT:", len(emails))

    emails = []
    page_token = None

    while True:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=100,
            pageToken=page_token
        ).execute()

        messages = results.get("messages", [])
        for msg in messages:
            email = get_email_content(service, msg["id"])
            emails.append(email)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    print(f"📬 GMAIL FETCHED {len(emails)} EMAILS")

    if return_service:
        return emails, service

    return emails
