def detect_merchant(text: str):
    if not text:
        return None

    t = text.lower()
    t = " ".join(t.split())

    # --------------------------------
    # 🥇 MOST SPECIFIC FIRST
    # --------------------------------

    # Swiggy Instamart
    if "instamart" in t:
        return "Swiggy Instamart"

    # Blinkit
    if "blinkit" in t:
        return "Blinkit"

    # Zepto
    if "zepto" in t:
        return "Zepto"

    # Amazon Fresh (groceries only)
    if "amazon fresh" in t or "amazonfresh" in t:
        return "Amazon Fresh"

    # Flipkart Minutes (groceries)
    if "flipkart minutes" in t or "flipkartminutes" in t:
        return "Flipkart Minutes"

    # --------------------------------
    # 🥈 Restaurants
    # --------------------------------

    if "zomato" in t:
        return "Zomato"

    # IMPORTANT: must stay after instamart check
    if "swiggy" in t:
        return "Swiggy"

    return None


def detect_category(merchant: str):
    if not merchant:
        return "Others"

    m = merchant.lower().strip()

    # Groceries
    if m in ("swiggy instamart", "blinkit", "zepto", "amazon fresh", "bigbasket", "grofers", "flipkart minutes"):
        return "Grocery"

    # Restaurants
    if m in ("swiggy", "zomato"):
        return "Restaurant"

    return "Others"