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

    merchant = (
        detect_merchant(sender)
        or detect_merchant(subject)
        or detect_merchant(body)
    )

    if not merchant:
        return None

    category = detect_category(merchant)

    combined_text = (sender + subject).lower()
    is_bank_alert = any(bank in combined_text for bank in ["hdfc", "icici", "axis", "sbi"])

    # ---------------- ZOMATO ----------------
    if merchant == "Zomato":

        # 1️⃣ Try strict order total from body
        match = re.search(
            r"(order total|grand total|amount paid|total payable)[^\d₹]*₹\s*([\d,]+(?:\.\d{1,2})?)",
            body,
            re.IGNORECASE
        )


        if match:
            amount = float(match.group(2).replace(",", ""))
            if amount >= 100:
                return {
                    "merchant": "Zomato",
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        # 2️⃣ If no app email match but it's bank alert
        if is_bank_alert:
            amount = extract_amount(subject) or extract_amount(body)
            if amount and amount >= 100:
                return {
                    "merchant": "Zomato",
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        return None

    # ---------------- SWIGGY ----------------
    if merchant == "Swiggy":

        # 1️⃣ Strict order total match
        match = re.search(
            r"order total\s*[:\-]?\s*₹\s*([\d,]+(?:\.\d{1,2})?)",
            body,
            re.IGNORECASE
        )

        if match:
            amount = float(match.group(1).replace(",", ""))
            if amount >= 100:
                return {
                    "merchant": "Swiggy",
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        # 2️⃣ PDF fallback
        pdf = extract_amount_from_pdf(email, service)
        if pdf and pdf.get("amount"):
            return {
                "merchant": "Swiggy",
                "category": category,
                "amount": round(pdf["amount"], 2),
                "date": date,
                "source_id": source_id,
            }

        # 3️⃣ Bank fallback
        if is_bank_alert:
            amount = extract_amount(subject) or extract_amount(body)
            if amount and amount >= 100:
                return {
                    "merchant": "Swiggy",
                    "category": category,
                    "amount": round(amount, 2),
                    "date": date,
                    "source_id": source_id,
                }

        return None

    # ---------------- BANK-ONLY MERCHANTS ----------------
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
