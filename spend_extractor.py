# spend_extractor.py
from bs4 import BeautifulSoup
import re
from datetime import datetime

MERCHANT_CATEGORY_MAP = {
    "swiggy": "Food Delivery",
    "zomato": "Food Delivery",
    "blinkit": "Grocery",
    "instamart": "Grocery",
    "zepto": "Grocery",
    "amazon": "Shopping",
    "homeshop18": "Shopping",
}


def detect_merchant(sender: str) -> str:
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


def detect_category(merchant: str) -> str:
    if not merchant:
        return "Other"
    return MERCHANT_CATEGORY_MAP.get(merchant.lower(), "Other")


def extract_amount(text: str):
    if not text:
        return None

    # Strip HTML → plain text
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(" ")

    # ₹349 or Rs. 349
    match = re.search(r"(₹|Rs\.?)\s*([0-9,]+)", clean_text)
    if match:
        return int(match.group(2).replace(",", ""))

    # Swiggy fallback
    match = re.search(r"Total\s+Paid\s*([0-9,]+)", clean_text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))

    return None


def normalize_date(date_str: str):
    try:
        return datetime.strptime(date_str[:25], "%a, %d %b %Y %H:%M:%S")
    except Exception:
        return None


def extract_spend(email: dict):
    print(">>> EXTRACT_SPEND SUBJECT:", email.get("Subject"))

    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date = email.get("Date", "")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    amount = extract_amount(body) or extract_amount(subject)

    spend = {
        "merchant": merchant,
        "category": category,
        "amount": amount,
        "date": normalize_date(date),
	"source_id": email.get("source_id")
    }

    print(">>> EXTRACT_SPEND RESULT:", spend)
    return spend
