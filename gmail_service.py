from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone, timedelta
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

    # Start of month
    start_date = datetime(year, mon, 1)

    # First day of next month
    if mon == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, mon + 1, 1)

    # Gmail 'after:' is exclusive → subtract 1 day
    start_for_query = (start_date - timedelta(days=1)).strftime("%Y/%m/%d")
    end_for_query = end_date.strftime("%Y/%m/%d")

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
        f'after:{start_for_query} before:{end_for_query}'
    )

    print("QUERY:", query)
