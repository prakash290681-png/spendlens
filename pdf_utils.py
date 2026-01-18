import base64
import re
import io
from PyPDF2 import PdfReader


def extract_amount_from_pdf(email: dict, service):
    attachments = email.get("attachments", [])

    for att in attachments:
        if att["mimeType"] != "application/pdf":
            continue

        att_data = service.users().messages().attachments().get(
            userId="me",
            messageId=email["id"],
            id=att["attachmentId"]
        ).execute()

        pdf_bytes = base64.urlsafe_b64decode(att_data["data"])
        reader = PdfReader(io.BytesIO(pdf_bytes))

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        # ₹ symbol + number OR Rs
        match = re.search(r"(₹|Rs\.?)\s?(\d+(\.\d{1,2})?)", text)
        if match:
            return float(match.group(2))

    return None
