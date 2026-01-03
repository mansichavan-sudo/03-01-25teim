import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from crmapp.models import SentMessageLog


@csrf_exempt
@require_POST
def rapbooster_delivery_webhook(request):
    """
    Receives delivery status updates from RapBooster
    """

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    message_id = payload.get("message_id")
    raw_status = payload.get("status")  # SENT / DELIVERED / READ / FAILED
    channel = payload.get("channel", "")

    if not message_id or not raw_status:
        return HttpResponseBadRequest("Missing message_id or status")

    # Normalize status
    status = raw_status.lower()

    if status not in ["sent", "delivered", "read", "failed"]:
        return JsonResponse({
            "ignored": True,
            "reason": "Unknown status",
            "received_status": raw_status
        })

    try:
        msg = SentMessageLog.objects.get(message_id=message_id)
    except SentMessageLog.DoesNotExist:
        return JsonResponse({
            "error": "Message not found",
            "message_id": message_id
        }, status=404)

    # ✅ Update delivery tracking
    msg.status = status
    msg.delivery_status = status
    msg.delivery_payload = payload
    msg.provider_response = json.dumps(payload)

    msg.save(update_fields=[
        "status",
        "delivery_status",
        "delivery_payload",
        "provider_response",
        "updated_at"
    ])

    return JsonResponse({
        "success": True,
        "message_id": message_id,
        "status": status,
        "channel": msg.channel
    })
