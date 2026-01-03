import requests
import os
import logging

logger = logging.getLogger(__name__)

RAPBOOSTER_API_KEY = os.getenv("RAPBOOSTER_API_KEY", "6538c8eff027d41e9151")
RAPBOOSTER_WA_URL = "https://api.rapbooster.com/v1/whatsapp/send"
RAPBOOSTER_EMAIL_URL = "https://api.rapbooster.com/v1/email/send"


def send_whatsapp(phone, message):
    payload = {
        "apikey": RAPBOOSTER_API_KEY,
        "mobile": phone,
        "msg": message
    }

    resp = requests.post(RAPBOOSTER_WA_URL, data=payload, timeout=15)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    success = resp.status_code == 200 and data.get("status") in ["success", "queued"]

    return success, data


def send_email(email, subject, message):
    payload = {
        "apikey": RAPBOOSTER_API_KEY,
        "to": email,
        "subject": subject,
        "message": message
    }

    resp = requests.post(RAPBOOSTER_EMAIL_URL, data=payload, timeout=15)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    success = resp.status_code == 200 and data.get("status") == "success"

    return success, data
