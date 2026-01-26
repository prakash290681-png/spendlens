# redeploy trigger
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf

import re

def extract_amount_by_labels(text: str):
    """
    Extracts the FINAL payable amount based on trusted labels.
    Returns float or None.
    """

    if not text:
        return None

    text = text.lower()

    LABEL_PATTERNS = [
        r"grand total\s*₹?\s*([\d,]+\.?\d*)",
        r"order total\s*₹?\s*([\d,]+\.?\d*)",
        r"invoice value\s*₹?\s*([\d,]+\.?\d*)",
        r"invoice total\s*₹?\s*([\d,]+\.?\d*)",
        r"total payable\s*₹?\s*([\d,]+\.?\d*)",
    ]

    matches = []

    for pattern in LABEL_PATTERNS:
        for m in re.finditer(pattern, text):
            amt = m.group(1).replace(",", "")
            try:
                matches.append(float(amt))
            except ValueError:
                continue

    if matches:
        # IMPORTANT: Swiggy often repeats totals → take LAST
        return matches[-1]

    return None

def extract_spend(email: dict, service):
    # 1️⃣ Detect merchant & category FIRST
    merchant = detect_merchant(email)
    category = detect_category(merchant)

    # Normalize date
    date = normalize_date(email.get("Date"))

    # Extract email body safely
    email_body = email.get("body", "")
    email_subject = email.get("subject", "")
    email_sender = email.get("from", "")

    merchant = detect_merchant(
        email_sender or email_subject or email_body
    )

    def build_spend(amount):
        return {
            "merchant": merchant,
            "category": category,
            "amount": amount,
            "date": date,
            "source_id": email.get("id")
        }

    # ---------------- SWIGGY LOGIC ----------------
    if merchant == "Swiggy":
        print("🍔 SWIGGY DETECTED — attempting email body extraction")

        # 1️⃣ Email body first
        amount = extract_amount_by_labels(email_body)

        if amount:
            print(f"✅ SWIGGY EMAIL BODY TOTAL FOUND: ₹{amount}")
            return build_spend(amount)

        # 2️⃣ PDF fallback
        print("📄 SWIGGY EMAIL BODY FAILED — trying PDF fallback")

        pdf_text = extract_pdf_text(email)

        if pdf_text:
            amount = extract_amount_by_labels(pdf_text)

            if amount:
                print(f"✅ SWIGGY PDF FINAL TOTAL FOUND: ₹{amount}")
                return build_spend(amount)

        # 3️⃣ Hard fail
        print("❌ SWIGGY TOTAL NOT FOUND — SKIPPING EMAIL")
        return None

    # ---------------- OTHER MERCHANTS ----------------
    amount = extract_amount_by_labels(email_body)

    if amount:
        return build_spend(amount)

    return None
