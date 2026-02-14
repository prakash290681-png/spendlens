def detect_merchant(text):
    print("🔥 DETECT MERCHANT CALLED 🔥")

    if not text:
        return None

    print("TEXT SAMPLE:", text[:120])   # 👈 ADD THIS
    
    t = text.lower()

    # 🥇 MOST SPECIFIC FIRST
    if "instamart" in t:
        return "Swiggy Instamart"

    if "blinkit" in t:
        return "Blinkit"

    if "zepto" in t:
        return "Zepto"
    
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
    if m in ["swiggy instamart", "blinkit", "zepto"]:
        return "Grocery"

    # restaurants
    if m in ["swiggy", "zomato"]:
        return "Restaurant"

    return "Others"


