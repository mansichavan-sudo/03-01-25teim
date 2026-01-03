import requests
from crmapp.models import SentMessageLog

STATUS_API = "https://rapbooster.ai/api/message_status/"
API_KEY = "6538c8eff027d41e9151"


def fetch_message_status(message_id):
    payload = {
        "apikey": API_KEY,
        "message_id": message_id
    }

    response = requests.post(STATUS_API, json=payload, timeout=10)

    try:
        return response.json()
    except:
        return {"status": "unknown"}
