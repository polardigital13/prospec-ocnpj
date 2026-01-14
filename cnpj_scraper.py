import os
import requests
from database import log_event

CNPJA_API_KEY = os.getenv("CNPJA_API_KEY")
CNPJA_BASE_URL = os.getenv("CNPJA_BASE_URL", "https://api.cnpja.com").rstrip("/")


def fetch_offices_by_founded_range(date_start: str, date_end: str):
    """
    GET /office?founded.gte=YYYY-MM-DD&founded.lte=YYYY-MM-DD
    Retorna com paginação via cursor (next).
    """
    if not CNPJA_API_KEY:
        raise RuntimeError("CNPJA_API_KEY não configurada.")

    url = f"{CNPJA_BASE_URL}/office"
    params = {
        "founded.gte": date_start,
        "founded.lte": date_end,
        "limit": 50,  # máximo de registros por requisição
    }

    r = requests.get(url, headers={"Authorization": CNPJA_API_KEY}, params=params, timeout=30)
    if r.status_code != 200:
        log_event("error", f"CNPJA /office {r.status_code}: {r.text[:500]}")
        r.raise_for_status()

    return r.json()


def extract_items(payload):
    """
    A API pode devolver lista direta ou objeto com itens/paginação.
    """
    if isinstance(payload, list):
        return payload
    return (
        payload.get("records") or
        payload.get("items") or
        payload.get("data") or
        payload.get("results") or
        []
    )


def normalize_office(item: dict) -> dict:
    """
    Normaliza pro seu schema do banco.
    """
    company = item.get("company") or {}
    address = item.get("address") or {}

    main_activity = item.get("mainActivity")
    if isinstance(main_activity, dict):
        cnae = main_activity.get("id")
    else:
        cnae = None

    # Extrai primeiro telefone
    phones = item.get("phones") or []
    phone = None
    if phones and isinstance(phones, list) and len(phones) > 0:
        phone_obj = phones[0]
        if isinstance(phone_obj, dict):
            area = phone_obj.get("area", "")
            number = phone_obj.get("number", "")
            phone = f"({area}){number}" if area and number else None
        else:
            phone = phone_obj
    
    # Extrai primeiro email
    emails = item.get("emails") or []
    email = None
    if emails and isinstance(emails, list) and len(emails) > 0:
        email_obj = emails[0]
        if isinstance(email_obj, dict):
            email = email_obj.get("address")
        else:
            email = email_obj

    street = address.get("street", "")
    number = address.get("number", "")
    district = address.get("district", "")
    city = address.get("city", "")
    state = address.get("state", "")
    endereco = f"{street} {number}, {district}, {city}-{state}".strip(" ,-")

    return {
        "cnpj": item.get("taxId"),
        "razao_social": company.get("name") or item.get("alias"),
        "telefone": phone,
        "email": email,
        "cidade": city,
        "uf": state,
        "cnae_principal": cnae,
        "data_abertura": item.get("founded"),
        "endereco": endereco,
    }
