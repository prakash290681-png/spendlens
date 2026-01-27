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

    # ignore noise (tips / retries)
    amounts = [a for a in amounts if a >= 100]

    return max(amounts) if amounts else None


# ---------- BANK ALERT ----------
def is_bank_alert(email: dict, merchant: str) -> bool:
    sender = (email.get("From") or "").lower()
    subject = (email.get("Subject") or "").lower()
    body = (email.get("Body") or "").lower()

    bank_senders = ["hdfc", "icici", "axis", "sbi", "kotak"]
    debit_words = ["debit", "spent", "txn", "transaction"]

    return (
        any(b in sender for b in bank_senders)
        and any(d in subject for d in debit_words)
        and merchant.lower() in body
    )


# ---------- MAIN ----------
def extract_spend(email: dict, service):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    date = normalize_date(date_str)

    def build_spend(amount):
        return {
            "merchant": merchant,
            "category": category,
            "amount": round(float(amount), 2),
            "date": date,
            "source_id": source_id,
        }

    # ================= SWIGGY ONLY =================
    if merchant == "Swiggy":

        # 1️⃣ PDF invoice — absolute source of truth
        pdf_amount = extract_amount_from_pdf(email, service)
        if pdf_amount:
            return build_spend(pdf_amount)

        # 2️⃣ Bank alert (card / wallet debit)
        if is_bank_alert(email, merchant):
            amount = extract_amount(subject) or extract_amount(body)
            if amount:
                return build_spend(amount)

        # 3️⃣ Swiggy email body total (food orders)
        amount = extract_swiggy_total_from_body(body)
        if amount:
            return build_spend(amount)

        # 4️⃣ Instamart / Genie fallback (no PDF, no keywords)
        fallback = (
            extract_swiggy_fallback_amount(body)
            or extract_swiggy_fallback_amount(subject)
        )
        if fallback:
            return build_spend(fallback)

        return None

    # ================= ALL OTHER MERCHANTS =================
    amount = extract_amount(body) or extract_amount(subject)
    if amount:
        return build_spend(amount)

    return None
