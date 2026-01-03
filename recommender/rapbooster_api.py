import requests
import json
from django.utils import timezone
from crmapp.models import (
    SentMessageLog,
    MessageTemplates,
    customer_details
)

# =========================================================
# CONFIG
# =========================================================

WHATSAPP_API = "https://rapbooster.ai/api/send_whatsapp/"
EMAIL_API = "https://rapbooster.ai/api/send_email/"
STATUS_API = "https://rapbooster.ai/api/message_status/"

API_KEY = "6538c8eff027d41e9151"

# 🔴 IMPORTANT
# True  → Local testing (no real API call)
# False → Real RapBooster API
MOCK_RAPBOOSTER = True


# =========================================================
# HELPERS
# =========================================================

def normalize_phone(phone):
    phone = str(phone).strip()
    if len(phone) == 10:
        phone = "91" + phone
    return phone


# =========================================================
# SEND WHATSAPP
# =========================================================

def send_to_rapbooster(msg_log):
    """
    Mock sending function — replace with real RapBooster API call
    """
    print(f"Sending message {msg_log.id} to RapBooster")
    # Optionally, set a fake message_id returned from RapBooster
    msg_log.message_id = f"MOCK_{msg_log.id}"
    msg_log.save(update_fields=["message_id"])


def send_whatsapp_message(phone, message, customer_name,
                          customer=None, template=None):

    phone = normalize_phone(phone)

    # 🧪 MOCK MODE
    if MOCK_RAPBOOSTER:
        fake_response = {
            "message_id": f"MOCK_WA_{int(timezone.now().timestamp())}",
            "status": "sent"
        }

        log = SentMessageLog.objects.create(
            template=template,
            customer=customer,
            customer_name=customer_name,
            recipient=phone,
            channel="whatsapp",
            rendered_body=message,
            rendered_subject="",
            status="sent",
            message_id=fake_response["message_id"],
            provider_response=json.dumps(fake_response),
            sent_at=timezone.now()
        )

        return log, fake_response

    # 🔵 REAL API CALL
    payload = {
        "apikey": API_KEY,
        "phone": phone,
        "message": message,
        "customer_name": customer_name
    }

    try:
        response = requests.post(WHATSAPP_API, json=payload, timeout=10)
        resp_json = response.json()
    except Exception as e:
        resp_json = {"error": str(e)}
        response = None

    message_id = resp_json.get("message_id") or resp_json.get("id")
    status = "sent" if response and response.status_code == 200 else "failed"

    log = SentMessageLog.objects.create(
        template=template,
        customer=customer,
        customer_name=customer_name,
        recipient=phone,
        channel="whatsapp",
        rendered_body=message,
        rendered_subject="",
        status=status,
        message_id=message_id,
        provider_response=json.dumps(resp_json),
        sent_at=timezone.now()
    )

    return log, resp_json


# =========================================================
# SEND EMAIL
# =========================================================

def send_email_message(email, subject, message, customer_name,
                       customer=None, template=None):

    # 🧪 MOCK MODE
    if MOCK_RAPBOOSTER:
        fake_response = {
            "message_id": f"MOCK_EMAIL_{int(timezone.now().timestamp())}",
            "status": "sent"
        }

        log = SentMessageLog.objects.create(
            template=template,
            customer=customer,
            customer_name=customer_name,
            recipient=email,
            channel="email",
            rendered_body=message,
            rendered_subject=subject,
            status="sent",
            message_id=fake_response["message_id"],
            provider_response=json.dumps(fake_response),
            sent_at=timezone.now()
        )

        return log, fake_response

    # 🔵 REAL API CALL
    payload = {
        "apikey": API_KEY,
        "email": email,
        "subject": subject,
        "message": message,
        "customer_name": customer_name
    }

    try:
        response = requests.post(EMAIL_API, json=payload, timeout=10)
        resp_json = response.json()
    except Exception as e:
        resp_json = {"error": str(e)}
        response = None

    message_id = resp_json.get("message_id") or resp_json.get("id")
    status = "sent" if response and response.status_code == 200 else "failed"

    log = SentMessageLog.objects.create(
        template=template,
        customer=customer,
        customer_name=customer_name,
        recipient=email,
        channel="email",
        rendered_body=message,
        rendered_subject=subject,
        status=status,
        message_id=message_id,
        provider_response=json.dumps(resp_json),
        sent_at=timezone.now()
    )

    return log, resp_json


# =========================================================
# CHECK DELIVERY STATUS (REAL TIME)
# =========================================================

def check_message_status(message_id):
    """
    Poll RapBooster for delivery status
    """

    # 🧪 MOCK MODE
    if MOCK_RAPBOOSTER:
        return {
            "message_id": message_id,
            "delivery_status": "delivered"
        }

    payload = {
        "apikey": API_KEY,
        "message_id": message_id
    }

    try:
        response = requests.post(STATUS_API, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# =========================================================
# HIGH-LEVEL RECOMMENDATION DISPATCH
# =========================================================

from crmapp.models import SentMessageLog, MessageTemplates
from crmapp.models import SentMessageLog, MessageTemplates


def send_recommendation_message(
    customer,
    message,
    channel="whatsapp",
    subject=""
):
    # Resolve template
    template = MessageTemplates.objects.filter(
        message_type=channel,
        is_active=True
    ).first()

    if not template:
        raise Exception("No active template")

    # Resolve recipient
    if channel == "whatsapp":
        recipient = normalize_phone(customer.primarycontact)
    else:
        recipient = customer.primaryemail

    if not recipient:
        raise Exception("Recipient missing")

    # 1️⃣ Create log FIRST (queued)
    log = SentMessageLog.objects.create(
        customer=customer,
        template=template,
        recipient=recipient,
        channel=channel,
        rendered_subject=subject or template.subject,
        rendered_body=message,
        status="queued",
        provider_response="{}",
        delivery_status="queued"
    )

    # 2️⃣ MOCK MODE
    if MOCK_RAPBOOSTER:
        log.status = "sent"
        log.delivery_status = "delivered"
        log.message_id = f"MOCK_{log.id}"
        log.save()

        return 200, {"mock": True}, log.message_id

    # 3️⃣ REAL API
    payload = {
        "apikey": API_KEY,
        "phone": recipient,
        "message": message,
        "customer_name": customer.fullname
    }

    response = requests.post(WHATSAPP_API, json=payload, timeout=10)
    resp_json = response.json()

    log.message_id = resp_json.get("message_id")
    log.status = "sent" if response.status_code in (200, 201, 202) else "failed"
    log.delivery_status = log.status
    log.provider_response = json.dumps(resp_json)
    log.save()

    return response.status_code, resp_json, log.message_id
