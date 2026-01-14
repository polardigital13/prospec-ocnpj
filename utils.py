import os
from datetime import datetime
import pytz
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
tz = pytz.timezone(TIMEZONE)


def is_business_hours() -> bool:
    start = int(os.getenv("HORA_INICIO", "9"))
    end = int(os.getenv("HORA_FIM", "18"))
    now = datetime.now(tz)

    # seg(0) .. dom(6)
    weekday_ok = now.weekday() <= 4
    hour_ok = start <= now.hour < end
    return weekday_ok and hour_ok


def to_e164_br(phone_raw: str):
    if not phone_raw:
        return None
    try:
        p = phonenumbers.parse(phone_raw, "BR")
        if not phonenumbers.is_valid_number(p):
            return None
        return phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        return None


def today_str() -> str:
    return datetime.now(tz).strftime("%Y-%m-%d")
