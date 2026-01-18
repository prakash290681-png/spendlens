import re
from datetime import datetime
from pdf_utils import extract_amount_from_pdf
from bs4 import BeautifulSoup

# -----------------------------
# Merchant → Category mapping
# -----------------------------
MERCHANT_CATEGORY_MAP = {
    "zomato": "Food Delivery",
    "swiggy": "Food Delivery",
    "instamart": "Food Delivery",
    "amazon": "Shopping",
}

# -----------------------------
# Merchant detection
# -----------------------------
def detect_merchant(sender: str) -> str:
    s = sender.lower()

    if "zomato" in s:
        return "Zomato"
    if "swiggy" in s or "@swiggy" in s or "noreply@swiggy" in s:
        return "Swiggy"
    if "instamart" in s:
        return "Instamart"
    if "amazon" in s:
        return "Amazon"

    return "Unknown"


def detect_category(merchant: str) -> str:
    if not merchant:
        return "Other"
    return MERCHANT_CATEGORY_MAP.get(merchant.lower(), "Other")


# -----------------------------
# Amount extraction (SAFE)
# -----------------------------
def extract_amount(text: str):
    if not text:
        return None

    # Normalize whitespace
    clean = " ".join(text.replace("\xa0", " ").split())

    patterns = [
        r"₹\s?([0-9]+(?:\.[0-9]{1,2})?)",
        r"Rs\.?\s?([0-9]+(?:\.[0-9]{1,2})?)",
        r"Order Total\s*₹?\s?([0-9]+(?:\.[0-9]{1,2})?)",
        r"Grand Total\s*₹?\s?([0-9]+(?:\.[0-9]{1,2})?)",
        r"Total Amount\s*₹?\s?([0-9]+(?:\.[0-9]{1,2})?)",
    ]

    for p in patterns:
        m = re.search(p, clean, re.IGNORECASE)
        if m:
            return float(m.group(1))

    return None


# -----------------------------
# Date normalization
# -----------------------------
def normalize_date(date_str: str):
    try:
        return datetime.strptime(date_str[:25], "%a, %d %b %Y %H:%M:%S")
    except Exception:
        return datetime.utcnow()


# -----------------------------
# MAIN ENTRY (THIS WAS MISSING)
# -----------------------------
def extract_spend(email: dict):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    attachments = email.get("Attachments", [])
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)

    amount = extract_amount(body) or extract_amount(subject)

    # fallback to PDF attachment parsing if amount not found
    if amount is None and merchant == "Swiggy":
        print(">>> TRYING PDF FALLBACK FOR SWIGGY")
        amount = extract_amount_from_pdf(email)

        print(">>> TRYING PDF ATTACHMENT PARSING FOR AMOUNT <<<")
        for att in attachments:
            if att["mimeType"] == "application/pdf":
                amount = extract_amount_from_pdf(att[attachments])
                if amount:
                    print (">>>Swiggy amount from PDF:", amount)
                    break
            
    date = normalize_date(date_str)

    return {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": date,
        "source_id": source_id,
    }

    print(">>> EXTRACT_SPEND RESULT:", spend)
    return spend
