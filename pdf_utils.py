import base64
import io
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from pdfminer.high_level import extract_text
import re

def extract_amount_from_pdf(attachment_id, service):
    att = service.users().messages().attachments().get(
        userId="me",
        messageId="me",
        id=attachment_id
    ).execute()

    data = base64.urlsafe_b64decode(att["data"])
    text = extract_text(io.BytesIO(data))

    match = re.search(r'₹\s?([\d,]+\.?\d*)', text)
    if match:
        return float(match.group(1).replace(",", ""))

    return None
