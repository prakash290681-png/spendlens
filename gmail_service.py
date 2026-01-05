from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def fetch_recent_emails(access_token: str, max_results=10):
    creds = Credentials(token=access_token)

    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = msg_data["payload"]["headers"]
        email = {
            h["name"]: h["value"]
            for h in headers
        }
        emails.append(email)

    return emails
