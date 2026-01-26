from utils import detect_merchant, detect_category
from date_utils import normalize_date
from pdf_utils import extract_amount_from_pdf

from html import unescape
import re

def strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_amount_by_labels(text: str):
    if not text:
        return None

    text = text.lower()

    LABEL_PATTERNS = [
        r"grand total\s*₹?\s*([\d,]+\.?\d*)",
        r"order total\s*₹?\s*([\d,]+\.?\d*)",
        r"invoice value\s*₹?\s*([\d,]+\.?\d*)",
        r"invoice total\s*₹?\s*([\d,]+\.?\d*)",
        r"total payable\s*₹?\s*([\d,]+\.?\d*)",
        r"total amount\s*₹?\s*([\d,]+\.?\d*)",
        r"item total\s*₹?\s*([\d,]+\.?\d*)",
        r"total\s*₹?\s*([\d,]+\.?\d*)",
    ]

    matches = []

    for pattern in LABEL_PATTERNS:
        for m in re.finditer(pattern, text):
            try:
                matches.append(float(m.group(1).replace(",", "")))
            except ValueError:
                pass

    # Swiggy repeats totals → last one is final
    return matches[-1] if matches else None


def extract_spend(email: dict, service):
    # --- Extract safe text ---
    sender = (email.get("From") or "").lower()
    subject = (email.get("Subject") or "").lower()

    print("EXTRACT START:", sender, "|", subject)

    email_body = email.get("Body", "") or email.get("body", "")
    email_subject = email.get("Subject", "") or email.get("subject", "")
    email_sender = email.get("From", "") or email.get("from", "")

    combined_text = f"{email_sender} {email_subject} {email_body}"

    # --- Detect merchant & category ---
    merchant = detect_merchant(combined_text)
    category = detect_category(merchant)

    # --- Normalize date ---
    date = normalize_date(email.get("Date"))

    def build_spend(amount):
        return {
            "merchant": merchant,
            "category": category,
            "amount": amount,
            "date": date,
            "source_id": email.get("id"),
        }

    # ================= SWIGGY =================
    if merchant == "Swiggy":
        print("🍔 SWIGGY DETECTED — attempting email body extraction")

        print("AMOUNT EXTRACTOR CALLED(EMAIL BODY)")
        clean_text = strip_html(combined_text)
        amount = extract_amount_by_labels(clean_text)

        
        if amount:
            print(f"✅ SWIGGY EMAIL BODY TOTAL FOUND: ₹{amount}")
            return build_spend(amount)

        print("📄 SWIGGY EMAIL BODY FAILED — trying PDF fallback")
        amount = extract_amount_from_pdf(email, service)

        if amount:
            print(f"✅ SWIGGY PDF FINAL TOTAL FOUND: ₹{amount}")
            return build_spend(amount)

        print("❌ SWIGGY TOTAL NOT FOUND — SKIPPING EMAIL")
        return None

    # ============== OTHER MERCHANTS ==============
    print("AMOUNT INPUT PREVIEW:", combined_text[:500])
    print("AMOUNT EXTRACTOR CALLED (COMBINED TEXT)")

    amount = extract_amount_by_labels(combined_text)
    if amount:
        return build_spend(amount)

    return None
