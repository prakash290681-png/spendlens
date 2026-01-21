import base64
import io
import re
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
            full_text += "\n" + page_text

        print(">>> PDF TEXT LEN:", len(full_text))

        # ✅ Swiggy-specific totals (real templates)
        patterns = [
            r"Grand\s*Total\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Total\s*Bill\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Amount\s*Paid\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Paid\s*₹\s*(\d+(\.\d{1,2})?)",
        ]

        for p in patterns:
            m = re.search(p, full_text, re.IGNORECASE)
            if m:
                amount = float(m.group(1))
                print(">>> PDF MATCHED TOTAL:", amount)
                return amount

        print(">>> PDF NO VALID TOTAL FOUND")

    return None
