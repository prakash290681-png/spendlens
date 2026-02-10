def detect_merchant(text: str):
    if not text:
        return None

    t = text.lower()

    # Swiggy
    if "swiggy" in t or "instamart" in t:
        return "Swiggy"

    # Zomato (food, instamart, bank alerts)
    if "zomato" in t:
        return "Zomato"
    
    return None


def detect_category(merchant: str) -> str:
    if merchant in ("Zomato", "Swiggy"):
        return "Food Delivery"
    return "Other"
