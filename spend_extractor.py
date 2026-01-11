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

def detect_merchant(sender):
    s = sender.lower()

    if "zomato" in s:
        return "Zomato"
    if "swiggy" in s:
        return "Swiggy"
    if "amazon" in s:
        return "Amazon"
    if "homeshop18" in s:
        return "HomeShop18"

    return "Unknown"



import re

def extract_amount(text: str):
    if not text:
        return None

    match = re.search(r"(₹|Rs\.?)\s?([0-9,]+)", text)
    if not match:
        return None

    return int(match.group(2).replace(",", ""))



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

