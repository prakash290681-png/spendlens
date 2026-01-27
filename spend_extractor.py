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

    # ⚠️ Generic extractor should take FIRST (used by Zomato)
    return float(matches[0].replace(",", ""))


# ---------- SWIGGY BODY TOTAL ----------
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

    # ✅ LAST total = full order value (fixes ₹483, ₹783)
    return totals[-1] if totals else None


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

    def build_spend(amount, is_alert=False):
        return {
            "merchant": merchant,
            "category": category,
            "amount": round(float(amount), 2),
            "date": date,
            "source_id": source_id,
            "is_alert": is_alert,
        }

    # ================= SWIGGY ONLY =================
    if merchant == "Swiggy":

        # 1️⃣ Bank alert (HIGHEST priority)
        if is_bank_alert(email, merchant):
            amount = extract_amount(subject) or extract_amount(body)
            if amount:
                return build_spend(amount, is_alert=True)

        # 2️⃣ Swiggy email BODY total (preferred over PDF)
        amount = extract_swiggy_total_from_body(body)
        if amount:
            return build_spend(amount)

        # 3️⃣ PDF fallback (last resort only)
        amount = extract_amount_from_pdf(email, service)
        if amount:
            return build_spend(amount)

        return None

    # ================= ALL OTHER MERCHANTS (ZOMATO UNTOUCHED) =================
    amount = extract_amount(body) or extract_amount(subject)
    if amount:
        return build_spend(amount)

    return None
