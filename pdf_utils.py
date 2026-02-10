import re

def extract_amount_from_pdf(email: dict, service):
    """
    Best-effort PDF parsing.
    If PDF is encrypted / unreadable → return None safely.
    """

    try:
        # --- your existing logic to download PDF bytes ---
        # Example (adjust if names differ):
        pdf_bytes = email.get("pdf_bytes")
        if not pdf_bytes:
            return None

        import pdfplumber
        from io import BytesIO

        text = ""

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += "\n" + page_text

        # --- extract amounts ---
        matches = re.findall(
            r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )

        amounts = []
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                if val >= 100:
                    amounts.append(val)
            except ValueError:
                pass

        if not amounts:
            return {
                "text": text,
                "amount": None,
            }

        return {
            "text": text,
            "amount": max(amounts),
        }

    except Exception as e:
        # 🔒 THIS IS THE IMPORTANT PART
        # Encrypted / corrupted PDFs land here
        print("⚠️ PDF skipped safely:", str(e))
        return None
