import os
import time
import requests
from datetime import datetime
from database import log_event
from utils import to_e164_br

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID", "3EA5E0B8F67E81D0391B3A66A58532E9")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "C558A2FB2D68CBD1E6533B45")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io").rstrip("/")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "11911346396")


def send_text(phone_e164: str, text: str):
    """
    Envia mensagem via Z-API com token no header.
    """
    if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
        raise RuntimeError("ZAPI_INSTANCE_ID / ZAPI_TOKEN não configurados.")

    url = f"{ZAPI_BASE_URL}/instances/{ZAPI_INSTANCE_ID}/send-text"
    headers = {"Client-Token": ZAPI_TOKEN}
    payload = {"phone": phone_e164, "message": text}

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        log_event("error", f"ZAPI status={r.status_code} body={r.text[:500]}")
        return {"ok": False, "status": r.status_code, "error": r.text}

    return {"ok": True, "data": r.json()}


def sleep_interval(seconds: int):
    time.sleep(max(0, int(seconds)))


def now_iso():
    return datetime.utcnow().isoformat()

def notify_admin_new_lead(cnpj: str, razao_social: str, cidade: str, uf: str, segmento: str):
    """
    Notifica o admin via WhatsApp quando um novo CNPJ é adicionado.
    """
    if not ADMIN_PHONE:
        log_event("warning", "ADMIN_PHONE não configurado. Notificação não enviada.")
        return {"ok": False, "error": "ADMIN_PHONE não configurado"}

    try:
        admin_e164 = to_e164_br(ADMIN_PHONE)
    except Exception as e:
        log_event("error", f"Erro ao converter ADMIN_PHONE: {str(e)}")
        return {"ok": False, "error": str(e)}

    message = (
        f"🆕 *NOVO CNPJ ABERTO*\n\n"
        f"*Razão Social:* {razao_social}\n"
        f"*CNPJ:* {cnpj}\n"
        f"*Localização:* {cidade}, {uf}\n"
        f"*Segmento:* {segmento}\n\n"
        f"_Mensagem automática do Prospec CNPJ_"
    )

    result = send_text(admin_e164, message)
    if result.get("ok"):
        log_event("admin_notification", f"Notificação enviada para admin - CNPJ: {cnpj}")
    else:
        log_event("error", f"Falha ao enviar notificação ao admin: {result.get('error')}")
    
    return result