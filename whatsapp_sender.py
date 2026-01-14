import os
import time
import requests
from datetime import datetime
from database import log_event

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID", "3EA5E0B8F67E81D0391B3A66A58532E9")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "C558A2FB2D68CBD1E6533B45")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io").rstrip("/")


def send_text(phone_e164: str, text: str):
    """
    Ajuste o endpoint se a sua conta Z-API exigir variação.
    """
    if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
        raise RuntimeError("ZAPI_INSTANCE_ID / ZAPI_TOKEN não configurados.")

    url = f"{ZAPI_BASE_URL}/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    payload = {"phone": phone_e164, "message": text}

    r = requests.post(url, json=payload, timeout=30)
    if r.status_code not in (200, 201):
        log_event("error", f"ZAPI status={r.status_code} body={r.text[:500]}")
        return {"ok": False, "status": r.status_code, "error": r.text}

    return {"ok": True, "data": r.json()}


def sleep_interval(seconds: int):
    time.sleep(max(0, int(seconds)))


def now_iso():
    return datetime.utcnow().isoformat()
