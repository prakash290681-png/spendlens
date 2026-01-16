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

    # Remove HTML if present
    try:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(text, "html.parser").get_text(" ")
    except Exception:
        pass

    # ₹ 283.65 or Rs. 283 or 283.65
    match = re.search(r"(₹|Rs\.?)\s*([0-9]+(?:\.[0-9]{1,2})?)", text)
    if match:
        return float(match.group(2))

    # Swiggy-style fallback: "Total Paid 254"
    match = re.search(r"Total\s+(Paid|Amount)\s*[:\-]?\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
    if match:
        return float(match.group(2))

    return None
