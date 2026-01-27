def detect_merchant(text: str):
    if not text:
        return None

    text = text.lower()

    # Zomato
    if "zomato" in text:
        return "Zomato"

    # Swiggy (food, instamart, bank alerts)
    if (
        "swiggy" in text
        or "instamart" in text
        or "bundl" in text
    ):
        return "Swiggy"

    return None


def detect_category(merchant: str) -> str:
    if merchant in ["Zomato", "Swiggy"]:
        return "Food Delivery"

    return "Other"
