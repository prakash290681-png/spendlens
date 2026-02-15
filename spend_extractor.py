import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date


# ---------------- AMOUNT HELPERS ----------------

def extract_amount(text: str):
    if not text:
        return None

    patterns = [
        r"₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        r"inr\s*([\d,]+(?:\.\d{1,2})?)",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))

    return None


# ---------------- MAIN ----------------

def extract_spend(email: dict, service):

    sender = email.get("From", "") or ""
    subject = email.get("Subject", "") or ""
    body = email.get("Body", "") or ""
    date = normalize_date(email.get("Date"))
    source_id = email.get("id")

    clean_body = re.sub(r"\s+", " ", body)
    full_text = f"{subject} {body} {sender}".lower()

    print("======== EMAIL DEBUG ========")
    print("SUBJECT:", subject)
    print("BODY SAMPLE:", body[:500])
    print("SENDER:", sender)
    print("=============================")

    # ---------------- MERCHANT DETECTION ----------------

    # SUBJECT FIRST (most reliable)
    # 🔥 Hard override — Instamart must win FIRST
    if "instamart" in full_text:
        merchant = "Swiggy Instamart"
    else:
        merchant = detect_merchant(subject) or \
                detect_merchant(body) or \
                detect_merchant(sender)


    if not merchant:
        return None

    category = detect_category(merchant)

    combined_text = (sender + subject).lower()
    is_bank_alert = any(bank in combined_text for bank in ["hdfc", "icici", "axis", "sbi"])

    # ============================================================
    # ===================== ZOMATO ===============================
    # ============================================================

    if merchant == "Zomato":

        match = re.search(
            r"(order\s*total|amount\s*paid|grand\s*total|total)"
            r"[^\d₹]{0,80}₹?\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE
        )

        if match:
            amount = float(match.group(2).replace(",", ""))
            if amount >= 100:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        return None


    # ============================================================
    # ================= SWIGGY INSTAMART =========================
    # ============================================================

    if merchant == "Swiggy Instamart":

        match = re.search(
            r"(order\s*total|amount\s*paid|grand\s*total|total)"
            r"[^\d₹]{0,80}₹?\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE
        )

        if match:
            amount = float(match.group(2).replace(",", ""))
            if amount >= 100:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        return None


    # ============================================================
    # ================= SWIGGY RESTAURANT ========================
    # ============================================================

    if merchant == "Swiggy":

        # Strong label match first
        match = re.search(
            r"(order\s*total|grand\s*total|amount\s*paid|total\s*payable|total)"
            r"[^\d₹]{0,100}₹?\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE
        )

        if match:
            amount = float(match.group(2).replace(",", ""))
            if amount >= 100:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        # Smart fallback (avoid picking item total blindly)
        amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
        values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 100]

        if values:
            values.sort(reverse=True)

            # Avoid highest blindly (often item total)
            if len(values) >= 2:
                amount = values[1]
            else:
                amount = values[0]

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        # Bank fallback
        if is_bank_alert:
            amount = extract_amount(subject) or extract_amount(body)
            if amount and amount >= 100:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        return None

    return None
