import pdfplumber
import re
import tempfile
import os


def extract_amount_from_pdf(pdf_bytes: bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(pdf_bytes)
            pdf_path = f.name

        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Match ₹204, ₹ 204.50, Rs 204 etc
        match = re.search(r"(₹|Rs\.?)\s?(\d+(?:\.\d+)?)", text)
        if match:
            return float(match.group(2))

    except Exception as e:
        print("PDF parse error:", e)

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    return None
