import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("CNPJA_BASE_URL", "https://api.cnpja.com").rstrip("/")
KEY = os.getenv("CNPJA_API_KEY")

url = f"{BASE}/office"
params = {
    "founded.gte": "2026-01-14",
    "founded.lte": "2026-01-14",
    "page": 1
}
r = requests.get(url, headers={"Authorization": KEY}, params=params, timeout=30)
print("status:", r.status_code)
print(r.text[:2000])
