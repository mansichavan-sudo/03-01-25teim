import requests, json
from django.utils import timezone
from crmapp.models import SentMessageLog
from recommender.rapbooster_api import send_email_message,send_whatsapp_message

WHATSAPP_API = "https://rapbooster.ai/api/send_whatsapp/"
EMAIL_API = "https://rapbooster.ai/api/send_email/"
STATUS_API = "https://rapbooster.ai/api/message_status/"

API_KEY = "6538c8eff027d41e9151"


def fetch_message_status(message_id):
    payload = {
        "apikey": API_KEY,
        "message_id": message_id
    }

    response = requests.post(STATUS_API, json=payload, timeout=10)

    try:
        resp_json = response.json()
    except:
        return None, {"error": "Invalid JSON response"}

    return response.status_code, resp_json


def update_delivery_status(sent_log: SentMessageLog):
    if not sent_log.message_id:
        return False

    status_code, resp = fetch_message_status(sent_log.message_id)
    if not resp:
        return False

    sent_log.delivery_status = resp.get("status")   # delivered / read / failed
    sent_log.delivery_payload = resp
    sent_log.updated_at = timezone.now()
    sent_log.save(update_fields=[
        "delivery_status",
        "delivery_payload",
        "updated_at"
    ])

    return sent_log.delivery_status


from crmapp.models import customer_details, MessageTemplates

def send_recommendation_message(
    customer: customer_details,
    message: str,
    template: MessageTemplates = None,
    channel: str = "whatsapp"
):
    """
    High-level helper for recommendation delivery
    """

    if channel == "whatsapp":
        if not customer.primarycontact:
            return None, {"error": "Customer has no phone"}

        return send_whatsapp_message(
            phone=customer.primarycontact,
            message=message,
            customer_name=customer.fullname,
            customer=customer,
            template=template
        )

    elif channel == "email":
        if not customer.primaryemail:
            return None, {"error": "Customer has no email"}

        return send_email_message(
            email=customer.primaryemail,
            subject="Recommended for you",
            message=message,
            customer_name=customer.fullname,
            customer=customer,
            template=template
        )

    return None, {"error": "Invalid channel"}
