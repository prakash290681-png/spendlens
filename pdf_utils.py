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
            full_text += "\n" + page_text

        print(">>> FULL PDF TEXT PREVIEW:", full_text[:500])

        print(">>> PDF TEXT LEN:", len(full_text))
        # 🔍 DEBUG: show all currency amounts found
        all_matches = re.findall(
            r"(₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
            full_text,
            re.IGNORECASE
       )

        print(">>> ALL CURRENCY MATCHES:", [m[1] for m in all_matches])

        # 🎯 TARGET SWIGGY TOTALS ONLY
        patterns = [
            r"(Grand Total|Total Payable|Invoice Total|Invoice Value|Amount Paid)[^\d]*(₹|Rs\.?|INR)?\s*([\d,]+(\.\d{1,2})?)"
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                amount = float(match.group(3).replace(",", ""))
                print(">>> PDF MATCHED TOTAL:", amount)
                return amount

        print(">>> PDF NO VALID TOTAL FOUND")

    return None
