import io
import re
import base64
from PyPDF2 import PdfReader


def extract_amount_from_pdf(email: dict, service):
    attachments = email.get("attachments", [])

    for att in attachments:
        if att.get("mimeType") != "application/pdf":
            continue

        att_data = service.users().messages().attachments().get(
            userId="me",
            messageId=email["id"],
            id=att["attachmentId"]
        ).execute()

        pdf_bytes = base64.urlsafe_b64decode(att_data["data"])
        reader = PdfReader(io.BytesIO(pdf_bytes))

        full_text = ""

        for page in reader.pages:
            page_text = page.extract_text() or ""
            print(">>> PDF PAGE TEXT LEN:", len(page_text.strip()))  # ✅ ONE-LINE DEBUG
            full_text += page_text + "\n"

        if not full_text.strip():
            return None

	matches = re.findall(
    	   r"(?:₹\s*)?([0-9]{2,5}(?:\.[0-9]{1,2})?)",
    	   full_text
	)

	if matches:
    	   return float(matches[-1])  # last number = final total


    return None
