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
            full_text += (page.extract_text() or "") + "\n"

        print(">>> PDF TEXT LEN:", len(full_text))

        # ✅ PRIORITY-BASED EXTRACTION (Swiggy-safe)
        patterns = [
            r"Order Total\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Item Total\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Grand Total\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Amount Paid\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Invoice Total\s*₹\s*(\d+(\.\d{1,2})?)",
            r"Invoice Value\s*₹\s*(\d+(\.\d{1,2})?)",
        ]

        for p in patterns:
            match = re.search(p, full_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                print(">>> PDF MATCHED AMOUNT:", amount)
                return amount

        print(">>> PDF NO VALID TOTAL FOUND")
        return None
