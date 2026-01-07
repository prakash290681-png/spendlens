from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime
import time

def gmail_timestamp(dt: datetime) -> int:
    return int(time.mktime(dt.timetuple()))

def fetch_recent_emails(access_token: str, max_results=10):
    print(">>> fetch_recent_emails() CALLED <<<")

    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    if now.month == 12:
        end_of_month = datetime(now.year + 1, 1, 1)
    else:
        end_of_month = datetime(now.year, now.month + 1, 1)

    after_ts = gmail_timestamp(start_of_month)
    before_ts = gmail_timestamp(end_of_month)

    creds = Credentials(token=access_token)
    service = build("gmail", "v1", credentials=creds)

    MERCHANT_SENDERS = ["zomato", "swiggy", "amazon", "flipkart"]

    merchant_query = (
        "("
        + " OR ".join([f"from:{m}" for m in MERCHANT_SENDERS])
        + f") after:{after_ts} before:{before_ts}"
    )

    results = service.users().messages().list(
        userId="me",
        q=merchant_query,
        maxResults=500
    ).execute()
   
    print(">>> RAW GMAIL RESULTS:", results)
    print(">>> GMAIL MERCHANT QUERY RESULT KEYS:", results.keys())
    print(">>> GMAIL MERCHANT MESSAGE COUNT:", len(results.get("messages", [])))
    
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
        email = {h["name"]: h["value"] for h in headers}

        print("MERCHANT EMAIL FROM:", email.get("From"))
        print("MERCHANT EMAIL SUBJECT:", email.get("Subject"))
        print("-----")

        emails.append(email)

    return emails

