def detect_merchant(text: str | None):
    if not text:
        return "Unknown"

    text = text.lower()

    if "swiggy" in text:
        return "Swiggy"
    if "zomato" in text:
        return "Zomato"

    return "Unknown"

def detect_category(merchant: str) -> str:
    if merchant in ["Zomato", "Swiggy"]:
        return "Food Delivery"

    return "Other"
