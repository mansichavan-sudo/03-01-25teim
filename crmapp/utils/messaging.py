import requests
from django.utils import timezone
from crmapp.models import SentMessageLog

API_KEY = "YOUR_API_KEY"
WHATSAPP_API = "YOUR_WHATSAPP_ENDPOINT"
EMAIL_API = "YOUR_EMAIL_ENDPOINT"


def normalize_phone(phone):
    phone = str(phone).strip()
    if len(phone) == 10:
        phone = "91" + phone
    return phone


def send_whatsapp_message(phone: str, message: str, customer_name: str,
                          customer=None, template_id=None):

    phone = normalize_phone(phone)

    payload = {
        "apikey": API_KEY,
        "phone": phone,
        "message": message,
        "customer_name": customer_name
    }

    status = "error"
    resp_json = {}
    message_id = None

    try:
        response = requests.post(WHATSAPP_API, json=payload, timeout=10)

        try:
            resp_json = response.json()
        except:
            resp_json = {}

        message_id = resp_json.get("message_id") or resp_json.get("id")

        if response.status_code == 200:
            status = "sent"
        else:
            status = "failed"

    except Exception as e:
        resp_json = {"error": str(e)}
        status = "error"

    # ✅ LOG MESSAGE ALWAYS
    SentMessageLog.objects.create(
        recipient=phone,
        channel="whatsapp",
        rendered_body=message,
        rendered_subject="",
        sent_at=timezone.now(),
        status=status,
        provider_response=resp_json,
        template_id=template_id,
        customer_name=customer_name,
        message_id=message_id,
        customer_id=customer.id if customer else None
    )

    return status, resp_json, message_id


def send_message(
    *,
    customer,
    template,
    channel,
    recipient,
    send_func
):
    from crmapp.utils.template_renderer import render_dynamic_template
    from crmapp.models import SentMessageLog
    import json

    rendered_body = render_dynamic_template(template.body, customer.id)

    try:
        status, resp, message_id = send_func(
            recipient=recipient,
            message=rendered_body
        )

        SentMessageLog.objects.create(
            template=template,
            customer=customer,
            customer_name=customer.fullname,
            recipient=recipient,
            channel=channel,
            rendered_body=rendered_body,
            rendered_subject=template.subject or "",
            status=status,
            message_id=message_id,
            provider_response=json.dumps(resp),
        )

        return True

    except Exception as e:
        SentMessageLog.objects.create(
            template=template,
            customer=customer,
            customer_name=customer.fullname,
            recipient=recipient,
            channel=channel,
            rendered_body=rendered_body,
            rendered_subject=template.subject or "",
            status="error",
            provider_response=str(e),
        )
        return False
