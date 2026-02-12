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
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
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

    # ---- detect bank alert ----
    is_bank_alert = any(
        k in (sender + subject).lower()
        for k in ["hdfc", "icici", "axis", "sbi"]
    )


    # ---------------- ZOMATO ----------------
    if merchant == "Zomato":
        amount = extract_amount(body) or extract_amount(subject)
        if not amount or amount < 100:
            return None

        return {
            "merchant": "Zomato",
            "category": category,
            "amount": round(amount, 2),
            "date": date,
            "source_id": source_id,
        }

    # ---------------- SWIGGY ----------------
        # ---------------- SWIGGY ----------------
    if merchant == "Swiggy":

        # 1️⃣ STRICT Order Total match only
        order_total_match = re.search(
            r"order total\s*[:\-]?\s*₹\s*([\d,]+(?:\.\d{1,2})?)",
            body,
            re.IGNORECASE
        )

        if order_total_match:
            amount = float(order_total_match.group(1).replace(",", ""))
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

        # 3️⃣ If this is BANK alert and no app email detected
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
    # (ATM, transfers, utilities, etc.)
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
