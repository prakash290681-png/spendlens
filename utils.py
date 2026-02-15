def detect_merchant(text: str):
    if not text:
        return None

    t = text.lower().strip()

    # --------------------------------
    # 🥇 MOST SPECIFIC FIRST
    # --------------------------------

    # Instamart variations
    if "instamart" in t or "insta mart" in t:
        return "Swiggy Instamart"

    if "blinkit" in t:
        return "Blinkit"

    if "zepto" in t:
        return "Zepto"

    # --------------------------------
    # 🥈 General brands
    # --------------------------------

    if "zomato" in t:
        return "Zomato"

    # Important:
    # Only match plain Swiggy AFTER instamart check
    if "swiggy" in t:
        return "Swiggy"

    return None


def detect_category(merchant: str):
    if not merchant:
        return "Others"

    m = merchant.lower().strip()

    # Groceries
    if m in ("swiggy instamart", "blinkit", "zepto"):
        return "Grocery"

    # Restaurants
    if m in ("swiggy", "zomato"):
        return "Restaurant"

    return "Others"
