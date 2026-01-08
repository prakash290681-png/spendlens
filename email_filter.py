# email_filter.py

ORDER_SENDERS = [
    "swiggy",
    "zomato",
    "amazon",
    "blinkit",
    "instamart",
    "zepto"
]

ORDER_SUBJECT_KEYWORDS = [
    "order",
    "placed",
    "confirmed",
    "delivered",
    "invoice",
    "receipt"
]


def is_order_email(email):
    subject = email.get("Subject", "").lower()
    sender = email.get("From", "").lower()

    # ✅ Keep only real transaction emails
    if not any(word in subject for word in ["order", "ordered", "receipt", "invoice"]):
        return False

    return True
