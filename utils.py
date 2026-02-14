def detect_merchant(text):
    if not text:
        return None

    t = text.lower()

    # 🥇 MOST SPECIFIC FIRST
    if "instamart" in t:
        return "Swiggy Instamart"

    # 🥈 then general brands
    if "zomato" in t:
        return "Zomato"

    if "swiggy" in t:
        return "Swiggy"

    return None



def detect_category(merchant):
    if not merchant:
        return "Others"

    m = merchant.lower()

    # groceries
    if "instamart" in m:
        return "Grocery"

    # restaurants
    if m in ["swiggy", "zomato"]:
        return "Restaurant"

    return "Others"

