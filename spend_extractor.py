import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf


# ---------- GENERIC AMOUNT ----------
def extract_amount(text: str):
    if not text:
        return None

    matches = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", text)
    if not matches:
        return None

    return float(matches[0].replace(",", ""))


# ---------- SWIGGY BODY TOTAL (KEYWORDS) ----------
def extract_swiggy_total_from_body(text: str):
    if not text:
        return None

    text = text.lower()
    patterns = [
        r"(order total|grand total|amount paid|total payable)[^\d₹]*₹?\s*([\d,]+(?:\.\d{1,2})?)"
    ]

    totals = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            totals.append(float(m.group(2).replace(",", "")))

    return totals[-1] if totals else None


# ---------- SWIGGY FALLBACK (INSTAMART / GENIE) ----------
def extract_swiggy_fallback_amount(text: str):
    if not text:
        return None

    matches = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", text)
    if not matches:
        return None

    amounts = [float(m.replace(",", "")) for m in matches]

    # Ignore tips / retries / noise
    amounts = [a for a in amounts if a >= 100]

    return max(amounts) if amounts else None


# ---------- BANK ALERT ----------
def is_bank_alert(email: dict) -> bool:
    sender = (email.get("From") or "").lower()
    subject = (email.get("Subject") or "").lower()
    body = (email.get("Body") or "").lower()

    bank_senders = ["hdfc", "icici", "axis", "sbi", "kotak"]
    debit_words = ["debit", "spent", "txn", "transaction"]

    return (
        any(b in sender for b in bank_senders)
        and any(d in subject for d in debit_words)
        and "swiggy" in body
    )


# ---------- MAIN ----------
def extract_spend(email: dict, service):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    date = normalize_date(date_str)

    # =====================================================
    # 1️⃣ BANK ALERTS — HANDLE FIRST (GLOBAL, ISOLATED)
    # =====================================================
    if is_bank_alert(email):
        amount = extract_amount(subject) or extract_amount(body)
        if amount and amount >= 100:
            return {
                "merchant": "Swiggy",
                "category": "Food Delivery",
                "amount": round(float(amount), 2),
                "date": date,
                "source_id": source_id,
            }

    # =====================================================
    # 2️⃣ NORMAL MERCHANT FLOW
    # =====================================================
    merchant = (
        detect_merchant(sender)
        or detect_merchant(subject)
        or detect_merchant(body)
    )

    if not merchant:
        return None

    category = detect_category(merchant)

    def build_spend(amount):
        return {
            "merchant": merchant,
            "category": category,
            "amount": round(float(amount), 2),
            "date": date,
            "source_id": source_id,
        }

    # ================= SWIGGY =================
    if merchant == "Swiggy":

        # PDF invoice = absolute truth
        pdf_amount = extract_amount_from_pdf(email, service)
        if pdf_amount:
            return build_spend(pdf_amount)

        # Swiggy email body total (food orders)
        amount = extract_swiggy_total_from_body(body)
        if amount and amount >= 100:
            return build_spend(amount)

        # Instamart / Genie fallback
        fallback = (
            extract_swiggy_fallback_amount(body)
            or extract_swiggy_fallback_amount(subject)
        )
        if fallback:
            return build_spend(fallback)

        return None

    # ================= ZOMATO & OTHERS =================
    amount = extract_amount(body) or extract_amount(subject)
    if amount:
        return build_spend(amount)

    return None
