import re
from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf


# ---------- GENERIC AMOUNT ----------
def extract_amount(text: str):
    if not text:
        return None

    patterns = [
        r"₹\s*([\d,]+(?:\.\d{1,2})?)",
        r"rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        r"inr\s*([\d,]+(?:\.\d{1,2})?)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))

    return None



# ---------- SWIGGY BODY TOTAL (KEYWORDS) ----------
def extract_swiggy_total_from_body(text: str):
    if not text:
        return None

    text = text.lower()
    pattern = r"(order total|grand total|amount paid|total payable)[^\d₹]*₹?\s*([\d,]+(?:\.\d{1,2})?)"

    m = re.search(pattern, text)
    if m:
        return float(m.group(2).replace(",", ""))

    return None


# ---------- SWIGGY FALLBACK (INSTAMART / GENIE) ----------
def extract_swiggy_fallback_amount(text: str):
    if not text:
        return None

    matches = re.findall(r"₹\s*([\d,]+(?:\.\d{1,2})?)", text)
    amounts = [float(m.replace(",", "")) for m in matches if float(m.replace(",", "")) >= 100]

    return max(amounts) if amounts else None


# ---------- BANK ALERT ----------
def is_bank_alert(email: dict) -> bool:
    sender = (email.get("From") or "").lower()
    subject = (email.get("Subject") or "").lower()
    body = (email.get("Body") or "").lower()

    bank_senders = ["hdfc", "icici", "axis", "sbi", "kotak"]

    # IMPORTANT: debit words should be checked in BODY, not subject
    debit_words = ["debit", "debited", "spent", "txn", "transaction", "has been debited"]


    return (
        any(b in sender for b in bank_senders)
        and ("swiggy" in body or "swiggy" in email.get("snippet", "").lower())
        and any(d in (subject + " " + body) for d in debit_words)

    )

# ---------- MAIN ----------
def extract_spend(email: dict, service):
    sender = email.get("From", "")
    subject = email.get("Subject", "")
    body = email.get("Body", "")
    date = normalize_date(email.get("Date"))
    source_id = email.get("id") or email.get("Message-Id")

    # =====================================================
    # 1️⃣ BANK ALERTS (LOWEST PRIORITY)
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
        return None

    # =====================================================
    # 2️⃣ MERCHANT DETECTION
    # =====================================================
    merchant = (
        detect_merchant(sender)
        or detect_merchant(subject)
        or detect_merchant(body)
    )
    # --- FIX 2: Force Instamart to Swiggy ---
    if (
        "instamart" in (subject or "").lower()
        or "instamart" in (body or "").lower()
    ):
        merchant = "Swiggy"

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
    
    # =====================================================
    # 3️⃣ SWIGGY
    # =====================================================
    if merchant == "Swiggy":

        # ---------- PDF (HIGHEST PRIORITY) ----------
        pdf_data = extract_amount_from_pdf(email, service)
        if pdf_data:
            return {
                "merchant": "Swiggy",
                "category": "Food Delivery",
                "amount": pdf_data["amount"],
                "date": date,
                "source_id": pdf_data.get("order_id") or source_id,
            }

        # ---------- Swiggy email body ----------
        body_total = extract_swiggy_total_from_body(body)
        if body_total and body_total >= 100:
            return build_spend(body_total)

        # ---------- Instamart / Genie fallback ----------
        fallback = (
            extract_swiggy_fallback_amount(body)
            or extract_swiggy_fallback_amount(subject)
        )
        if fallback:
            return build_spend(fallback)

        return None

    # =====================================================
    # 4️⃣ ZOMATO
    # =====================================================
    if merchant == "Zomato":
        keywords = ["paid", "order total", "amount paid", "invoice"]

        text = (subject + " " + body).lower()
        if not any(k in text for k in keywords):
            return None

        amount = extract_amount(body) or extract_amount(subject)
        if amount:
            return build_spend(amount)

    return None
