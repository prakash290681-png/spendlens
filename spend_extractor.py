from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf
import re


def extract_amount(text: str):
    if not text:
        return None

    # ₹ 204.50 OR Rs 204.50
    match = re.search(r"(₹|Rs\.?)\s?(\d+(\.\d{1,2})?)", text)
    if match:
        return float(match.group(2))

    return None


def extract_spend(email: dict, service):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)

    amount = extract_amount(body) or extract_amount(subject)

    # ✅ PDF fallback ONLY for Swiggy
    if amount is None and merchant == "Swiggy":
        print(">>> TRYING SWIGGY PDF FALLBACK")
        amount = extract_amount_from_pdf(email, service)
        print(">>> SWIGGY PDF AMOUNT:", amount)
        print("PDF TEXT LENGTH:", len(text))


    date = normalize_date(date_str)

    spend = {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": date,
        "source_id": source_id,
    }

    print(">>> EXTRACT_SPEND RESULT:", spend)
    return spend
