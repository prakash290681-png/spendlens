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

def extract_by_priority(text: str):

    patterns = [
        r"to\s*pay.{0,40}?₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"amount\s*paid.{0,40}?₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"total\s*payable.{0,40}?₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"grand\s*total.{0,40}?₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"order\s*total.{0,40}?₹\s*([\d,]+(?:\.\d{1,2})?)",
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
    refund_words = ["refund", "refunded", "reversal", "credited"]

    if any(word in clean_body.lower() for word in refund_words):
        return None
    full_text = f"{subject} {body} {sender}"
    merchant = detect_merchant(full_text)
    if not merchant:
        return None

    category = detect_category(merchant)

    bank_keywords = ["hdfc", "icici", "axis", "sbi", "credit card", "debited", "spent"]

    combined_text = (sender + subject).lower()

    is_bank_alert = any(k in combined_text for k in bank_keywords)

    # ============================================================
    # ===================== ZOMATO ===============================
    # ============================================================

    if merchant == "Zomato":

        match = re.search(
            r"(order\s*total|amount\s*paid|grand\s*total|total\s*paid|total)"
            r".{0,200}?₹?\s*([\d,]+(?:\.\d{1,2})?)",
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

        amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
        values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 100]

        if values:
            amount = max(values)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

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


    # ============================================================
    # ================= SWIGGY INSTAMART =========================
    # ============================================================

    if merchant == "Swiggy Instamart":

        # Prefer bank alerts
        if is_bank_alert:
            amount = extract_amount(subject) or extract_amount(body)

            if amount and amount >= 50:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        match = re.search(
            r"(order\s*total|amount\s*paid|total\s*payable|grand\s*total)"
            r"[^\d₹]{0,100}₹?\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE
        )

        if match:
            amount = float(match.group(2).replace(",", ""))

            if amount >= 50:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
        values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 50]

        if values:
            amount = max(values)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        return None


    # ============================================================
    # ================= ZEPTO / BLINKIT ==========================
    # ============================================================

    if merchant in ("Zepto", "Blinkit"):

        amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
        values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 50]

        if values:
            amount = max(values)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        if is_bank_alert:
            amount = extract_amount(subject) or extract_amount(body)

            if amount and amount >= 50:
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

        priority_amount = extract_by_priority(clean_body)

        if priority_amount and priority_amount >= 100:
            return {
                "merchant": merchant,
                "category": category,
                "amount": round(priority_amount, 2),
                "date": date,
                "source_id": source_id,
            }

        match = re.search(
            r"(order\s*total|grand\s*total|amount\s*paid|total\s*payable)"
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

        # fallback: scan lines containing ₹
        amount_lines = re.findall(
            r"([^\n]{0,80}(?:to\s*pay|total\s*payable|amount\s*paid|grand\s*total|total)[^\n]{0,80}?₹\s*[\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE
        )
        
        values = []

        for line in amount_lines:

            lower = line.lower()

            ignore_words = [
                "discount",
                "promo",
                "coupon",
                "savings",
                "item total",
                "delivery fee",
                "tax",
            ]

            if any(word in lower for word in ignore_words):
                continue

            m = re.search(r"₹\s*([\d,]+(?:\.\d{1,2})?)", line)

            if not m:
                continue

            val = float(m.group(1).replace(",", ""))

            if val <= 0:
                continue

            if val >= 100:
                values.append(val)

        if values:

            amount = max(values)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        # bank alert fallback
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