def detect_merchant(sender: str) -> str:
    sender = sender.lower()

    if "zomato" in sender:
        return "Zomato"
    if "swiggy" in sender:
        return "Swiggy"

    return "Unknown"


def detect_category(merchant: str) -> str:
    if merchant in ["Zomato", "Swiggy"]:
        return "Food Delivery"

    return "Other"
