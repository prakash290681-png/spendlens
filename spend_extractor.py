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


def extract_amount(text: str):
    """
    Extracts amount like ₹1,234 or Rs. 1234
    """
    match = re.search(r"(₹|rs\.?)\s?([\d,]+)", text.lower())
    if match:
        return int(match.group(2).replace(",", ""))
    return None


def normalize_date(date_str: str):
    try:
        return datetime.strptime(date_str[:25], "%a, %d %b %Y")
    except:
        return None


def extract_spend(email: dict):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    date = email.get("Date", "")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    amount = extract_amount(subject)

    return {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": normalize_date(date)
    }
