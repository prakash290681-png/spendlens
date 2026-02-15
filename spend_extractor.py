import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf


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


def extract_swiggy_total_from_body(text: str):
    if not text:
        return None

    pattern = r"(order total|grand total|amount paid|total payable)[^\d₹]*₹?\s*([\d,]+(?:\.\d{1,2})?)"
    m = re.search(pattern, text.lower())
    if m:
        return float(m.group(2).replace(",", ""))

    return None


def extract_fallback_amount(text: str):
    if not text:
        return None

    matches = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", text)
    vals = [float(x.replace(",", "")) for x in matches if float(x.replace(",", "")) >= 100]
    return max(vals) if vals else None


# ---------------- MAIN ----------------

def extract_spend(email: dict, service):

    sender = email.get("From", "") or ""
    subject = email.get("Subject", "") or ""
    body = email.get("Body", "") or ""
    date = normalize_date(email.get("Date"))
    source_id = email.get("id")

    # Detect merchant (body first for specificity)
    merchant = (
        detect_merchant(body)
        or detect_merchant(subject)
        or detect_merchant(sender)
    )

    print("SUBJECT:", subject)
    print("DETECTED MERCHANT:", merchant)


    full_text = f"{subject} {body} {sender}".lower()
    if "instamart" in full_text:
        merchant = "Swiggy Instamart"
    
    print("---- MERCHANT DEBUG ----")
    print("SUBJECT:", subject)
    print("SENDER:", sender)
    print("DETECTED:", merchant)
    print("------------------------")

    if not merchant:
        return None

    category = detect_category(merchant)

    combined_text = (sender + subject).lower()
    is_bank_alert = any(bank in combined_text for bank in ["hdfc", "icici", "axis", "sbi"])

    # ---------------- ZOMATO ----------------
    if merchant == "Zomato":

        clean_body = re.sub(r"\s+", " ", body)

        match = re.search(
            r"(order\s*total|amount\s*paid|grand\s*total|total\s*₹?)"
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

        # fallback
        amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
        values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 100]

        if values:
            values.sort(reverse=True)
            amount = values[1] if len(values) > 1 else values[0]

            print("✅ RETURNING MERCHANT:", merchant)

            return {
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "date": date,
                "source_id": source_id,
            }

        return None


        # 2️⃣ If no app email match but it's bank alert
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

    # ---------------- SWIGGY ----------------
    if merchant == "Swiggy":

        clean_body = re.sub(r"\s+", " ", body)

        # 1️⃣ Strong label match
        match = re.search(
            r"(order\s*total|grand\s*total|amount\s*paid|total\s*payable|total\s*₹?)"
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

        # 2️⃣ If email subject contains "delivered" or "order placed"
        if "order" in subject.lower():
            amounts = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", clean_body)
            values = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) >= 100]

            if values:
                # choose second largest instead of max (avoids item total)
                values.sort(reverse=True)
                amount = values[1] if len(values) > 1 else values[0]
                print("✅ RETURNING MERCHANT:", merchant)

                return {
                    "merchant": merchant,
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        # 3️⃣ Bank fallback
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

