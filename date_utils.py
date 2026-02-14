from datetime import datetime
from email.utils import parsedate_to_datetime


def normalize_date(date_str: str):
    if not date_str:
        return None

    try:
        # Gmail / RFC 2822 date format
        return parsedate_to_datetime(date_str)
    except Exception:
        try:
            # fallback if something odd comes in
            return datetime.fromisoformat(date_str)
        except Exception:
            return None
