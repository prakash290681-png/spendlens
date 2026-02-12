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

    # Detect bank alerts
    combined_text = (sender + subject).lower()
    is_bank_alert = any(
        bank in combined_text
        for bank in ["hdfc", "icici", "axis", "sbi"]
    )

    # ❌ NEVER ingest bank alerts for Swiggy/Zomato
    if is_bank_alert and merchant in ("Swiggy", "Zomato"):
        return None

    # ---------------- ZOMATO ----------------
    if merchant == "Zomato":

        match = re.search(
            r"(order total|amount paid|grand total)[^\d₹]*₹\s*([\d,]+(?:\.\d{1,2})?)",
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

        return None

    # ---------------- SWIGGY ----------------
    if merchant == "Swiggy":

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

        # PDF fallback
        pdf = extract_amount_from_pdf(email, service)
        if pdf and pdf.get("amount"):
            return {
                "merchant": "Swiggy",
                "category": category,
                "amount": round(pdf["amount"], 2),
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
