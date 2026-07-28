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

    clean_body = re.sub(r"<[^>]+>", " ", body)
    clean_body = re.sub(r"\s+", " ", clean_body)

    full_text = f"{subject} {sender} {body}"
    merchant = detect_merchant(full_text)
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
            
        print("=" * 80)
        print("BLINKIT/ZEPTO PARSE FAILED")
        print("Subject:", subject)
        print("Merchant:", merchant)
        print("FROM:", sender)
        print("BODY:")
        print(clean_body[:3000])
        print("=" * 80)
        return None


# ============================================================
# ================= SWIGGY RESTAURANT ========================
# ============================================================

    if merchant == "Swiggy":

        print("=" * 80)
        print("SWIGGY EMAIL BODY")
        print(clean_body)
        print("=" * 80)

        payment_patterns = [
            r"paid\s*via\s*(?:credit/debit|credit\s*/\s*debit|credit|debit)\s*card.*?₹\s*([\d,]+(?:\.\d{1,2})?)",

            r"paid\s*via\s*upi.*?₹\s*([\d,]+(?:\.\d{1,2})?)",

            r"paid\s*via\s*bank.*?₹\s*([\d,]+(?:\.\d{1,2})?)",
        ]

        # --------------------------------------------
        # 1. Final payment amount
        # --------------------------------------------

        for pattern in payment_patterns:

            print("Trying:", pattern)
            print("Pattern =", repr(pattern))
            match = re.search(
                pattern,
                clean_body,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                amount = float(match.group(1).replace(",", ""))

                print("Matched payment:", amount)

                if amount >= 100:
                    return {
                        "merchant": merchant,
                        "category": category,
                        "amount": round(amount, 2),
                        "date": date,
                        "source_id": source_id,
                    }

        # --------------------------------------------
        # 2. Order Total / Grand Total
        # --------------------------------------------

        match = re.search(
            r"(order\s*total|grand\s*total|amount\s*paid|total\s*paid).*?₹\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            amount = float(match.group(2).replace(",", ""))

            print("Matched order total:", amount)

            if amount >= 100:
                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        # --------------------------------------------
        # 3. Largest amount
        # --------------------------------------------

        amounts = re.findall(
            r"₹\s*([\d,]+(?:\.\d{1,2})?)",
            clean_body
        )

        values = [
            float(a.replace(",", ""))
            for a in amounts
            if float(a.replace(",", "")) >= 100
        ]

        if values:

            amount = max(values)

            print("Fallback largest:", amount)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        # --------------------------------------------
        # 4. Bank alert
        # --------------------------------------------

        if is_bank_alert:

            amount = extract_amount(subject) or extract_amount(body)

            if amount and amount >= 100:

                print("Bank alert:", amount)

                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        print("=" * 80)
        print("SWIGGY PARSE FAILED")
        print(subject)
        print(clean_body[:3000])
        print("=" * 80)

        return None