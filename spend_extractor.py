# spend_extractor.py
import re
from datetime import datetime

MERCHANT_CATEGORY_MAP = {
    "swiggy": "Food Delivery",
    "zomato": "Food Delivery",
    "blinkit": "Grocery",
    "instamart": "Grocery",
    "zepto": "Grocery",
    "amazon": "Shopping"
}

def detect_merchant(sender: str) -> str:
    sender = sender.lower()
    for merchant in MERCHANT_CATEGORY_MAP:
        if merchant in sender:
            return merchant.capitalize()
    return "Unknown"


def detect_category(merchant: str) -> str:
    return MERCHANT_CATEGORY_MAP.get(merchant.lower(), "Other")

def extract_amount(text):
    # TEMP FIX: return dummy amount to test pipeline
    return 349


from datetime import datetime

def normalize_date(date_str: str):
    try:
        # Example: 'Thu, 02 Jan 2026 12:34:56 +0530'
        return datetime.strptime(date_str[:25], "%a, %d %b %Y %H:%M:%S")
    except Exception:
        # fallback to today if parsing fails
        return datetime.utcnow()



def extract_spend(email: dict):
    print(">>> EXTRACT_SPEND SUBJECT:", email.get("Subject"))

    sender = email.get("From", "")
    subject = email.get("Subject", "")
    date = email.get("Date", "")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    amount = extract_amount(subject)

    spend = {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": normalize_date(date)
    }

    print(">>> EXTRACT_SPEND RESULT:", spend)

    return spend

