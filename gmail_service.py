from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
import time
import base64


def gmail_timestamp(dt: datetime) -> int:
    return int(time.mktime(dt.timetuple()))


def extract_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(
                    part["body"]["data"]
                ).decode("utf-8", errors="ignore")
    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(
            payload["body"]["data"]
        ).decode("utf-8", errors="ignore")
    return ""


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


def fetch_recent_emails(access_token: str, return_service=False):
    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)

    START = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    END   = int(datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp())

    query = (
        '(subject:"Zomato" OR subject:"Swiggy") '
        f'after:{START} before:{END}'
    )

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=100
    ).execute()

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
        email["attachments"] = extract_attachments(msg_data["payload"])

        emails.append(email)

    if return_service:
        return emails, service

    return emails
