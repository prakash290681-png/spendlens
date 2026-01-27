import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf


# ---------- GENERIC AMOUNT ----------
def extract_amount(text: str):
    if not text:
        return None

    patterns = [
        r"(₹)\s*([\d,]+(\.\d{1,2})?)",
        r"([\d,]+(\.\d{1,2})?)\s*INR",
        r"Total\s*(Payable|Amount)[^\d]*(₹?\s*[\d,]+(\.\d{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num_match = re.search(r"[\d,]+(?:\.\d{1,2})?", match.group())
            if num_match:
                return float(num_match.group().replace(",", ""))

    return None


# ---------- SWIGGY BODY TOTAL (handles multi-item orders) ----------
def extract_swiggy_total_from_body(text: str):
    if not text:
        return None

    text = text.lower()

    patterns = [
        r"(order total|grand total|amount paid|total payable)[^\d₹]*₹?\s*([\d,]+(?:\.\d{1,2})?)"
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            matches.append(float(m.group(2).replace(",", "")))

    # last total = final payable
    return matches[-1] if matches else None


# ---------- BANK ALERT DETECTION ----------
def is_bank_alert(email: dict) -> bool:
    sender = (email.get("From") or "").lower()
    subject = (email.get("Subject") or "").lower()
    body = (email.get("Body") or "").lower()

    bank_senders = ["hdfc", "icici", "axis", "sbi", "kotak"]
    debit_words = ["debit", "spent", "transaction"]

    return (
        any(b in sender for b in bank_senders)
        and any(d in subject for d in debit_words)
        and "swiggy" in body
    )


# ---------- MAIN ----------
def extract_spend(email: dict, service):
    print("STEP 1 INPUT EMAIL SUBJECT:", email.get("Subject"))
    print("🔥🔥🔥 EXTRACT_SPEND FUNCTION CALLED 🔥🔥🔥")

    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date_str = email.get("Date", "")
    source_id = email.get("id") or email.get("Message-Id")

    merchant = detect_merchant(sender)
    category = detect_category(merchant)
    date = normalize_date(date_str)

    def build_spend(amount, is_alert=False):
        spend = {
            "merchant": merchant,
            "category": category,
            "amount": round(float(amount), 2),
            "date": date,
            "source_id": source_id,
        }
        if is_alert:
            spend["is_alert"] = True
        return spend


    # ================= SWIGGY ONLY =================
    if merchant == "Swiggy":

        # 1️⃣ Bank alert (HIGHEST PRIORITY, alert-only)
        if is_bank_alert(email):
            amount = extract_amount(body) or extract_amount(subject)
            if amount:
                return build_spend(amount, is_alert=True)

        # 2️⃣ Swiggy email body (correct total, multi-item safe)
        amount = extract_swiggy_total_from_body(body)
        if amount:
            return build_spend(amount)

        # 3️⃣ PDF fallback (last resort only)
        amount = extract_amount_from_pdf(email, service)
        if amount:
            return build_spend(amount)

        return None


    # ================= ALL OTHER MERCHANTS (ZOMATO UNCHANGED) =================
    amount = extract_amount(body) or extract_amount(subject)
    if amount:
        return build_spend(amount)

    return None
