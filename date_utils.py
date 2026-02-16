from datetime import datetime
from email.utils import parsedate_to_datetime
from datetime import timezone

def normalize_date(date_str: str):
    if not date_str:
        return None

    try:
        dt = parsedate_to_datetime(date_str)

        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Always convert to UTC
        return dt.astimezone(timezone.utc)

    except Exception:
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
