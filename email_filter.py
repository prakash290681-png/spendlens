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


def is_order_email(email: dict) -> bool:
    """
    Returns True if the email looks like an order/transaction email
    """
    sender = email.get("From", "").lower()
    subject = email.get("Subject", "").lower()

    # Check sender domain
    if any(sender_name in sender for sender_name in ORDER_SENDERS):
        return True

    # Check subject keywords
    if any(keyword in subject for keyword in ORDER_SUBJECT_KEYWORDS):
        return True

    return False
