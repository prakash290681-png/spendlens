import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf


def extract_amount(text: str):
    if not text:
        return None

    patterns = [
        r"(₹)\s*([\d,]+(\.\d{1,2})?)",
        r"([\d,]+(\.\d{1,2})?)\s*INR",
        r"Total\s*(Payable|Amount)[^\d]*(₹?\s*[\d,]+(\.\d{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_match = re.search(r"[\d,]+(?:\.\d{1,2})?", match.group())
            if num_match:
                return float(num_match.group().replace(",", ""))

    return None


def extract_spend(email: dict, service):
    print("STEP 1 INPUT EMAIL SUBJECT:", email.get("Subject"))
    print("🔥🔥🔥 EXTRACT_SPEND FUNCTION CALLED 🔥🔥🔥")

    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)

    amount = None

    # 🔒 SWIGGY: PDF ONLY — NO BODY / SUBJECT EXTRACTION
    if merchant == "Swiggy":
        pdf_amount = extract_amount_from_pdf(email, service)
        if pdf_amount is None:
            print("🚫 SWIGGY WITHOUT PDF — SKIPPING")
            return None
        amount = pdf_amount

    # ✅ ALL OTHER MERCHANTS (ZOMATO UNCHANGED)
    else:
        amount = extract_amount(body) or extract_amount(subject)

    if amount is not None:
        amount = round(float(amount), 2)

    date = normalize_date(date_str)

    spend = {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": date,
        "source_id": source_id,
    }

    print(">>> EXTRACT_SPEND RESULT:", spend)
    print("STEP 1 EXTRACTED SPEND:", spend)

    return spend
