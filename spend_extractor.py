import re
from datetime import datetime
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
    if "swiggy" in s:
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

    # normalize spaces
    text = text.replace("\n", " ").replace("\r", " ")

    # 1️⃣ ₹123 or Rs. 123
    m = re.search(r"(₹|Rs\.?)\s*([0-9]+(?:\.[0-9]{1,2})?)", text)
    if m:
        return float(m.group(2))

    # 2️⃣ Swiggy-style: "Total Paid 155" or "Total Paid: 155.00"
    m = re.search(r"Total\s+Paid[:\s]*([0-9]+(?:\.[0-9]{1,2})?)", text, re.I)
    if m:
        return float(m.group(1))

    # 3️⃣ Swiggy fallback: "Grand Total 204"
    m = re.search(r"Grand\s+Total[:\s]*([0-9]+(?:\.[0-9]{1,2})?)", text, re.I)
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
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    amount = extract_amount(body) or extract_amount(subject)
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
