from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime
import time
import base64


def gmail_timestamp(dt: datetime) -> int:
    return int(time.mktime(dt.timetuple()))


def extract_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/html" and "data" in part["body"]:
                return base64.urlsafe_b64decode(
                    part["body"]["data"]
                ).decode("utf-8", errors="ignore")
    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(
            payload["body"]["data"]
        ).decode("utf-8", errors="ignore")
    return ""


# ✅ NEW: attachment extractor
def extract_attachments(payload):
    attachments = []

    if "parts" not in payload:
        return attachments

    for part in payload["parts"]:
        filename = part.get("filename")
        body = part.get("body", {})

        if filename and filename.lower().endswith(".pdf"):
            attachment_id = body.get("attachmentId")
            if attachment_id:
                attachments.append({
                    "filename": filename,
                    "attachmentId": attachment_id,
                    "mimeType": part.get("mimeType"),
                })

    return attachments


def fetch_recent_emails(access_token: str, max_results=50):
    print(">>> fetch_recent_emails() CALLED <<<")

    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)

    final_query = (
        '(subject:"Your Zomato order" OR subject:"Your Swiggy order")'
    )

    results = service.users().messages().list(
        userId="me",
        q=final_query,
        maxResults=500
    ).execute()

    print(">>> RAW GMAIL RESULTS:", results)
    print(">>> GMAIL MERCHANT MESSAGE COUNT:",
          len(results.get("messages", [])))

    messages = results.get("messages", [])
    emails = []

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

        # ✅ THIS IS THE KEY FIX
        email["Attachments"] = extract_attachments(msg_data["payload"])

        print("MERCHANT EMAIL FROM:", email.get("From"))
        print("MERCHANT EMAIL SUBJECT:", email.get("Subject"))
        print("ATTACHMENTS:", email["Attachments"])
        print("-----")

        emails.append(email)

    return emails
