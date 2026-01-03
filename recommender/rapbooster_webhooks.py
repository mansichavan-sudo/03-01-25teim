from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from crmapp.models import SentMessageLog


@csrf_exempt
def rapbooster_delivery_callback(request):
    """
    RapBooster delivery webhook
    """

    try:
        data = json.loads(request.body.decode())

        provider_message_id = (
            data.get("message_id") or
            data.get("id")
        )

        delivery_status = data.get("status", "").upper()
        # Example: DELIVERED, FAILED, READ

        if not provider_message_id:
            return JsonResponse({"error": "Missing message_id"}, status=400)

        log = SentMessageLog.objects.filter(
            message_id=provider_message_id
        ).first()

        if not log:
            return JsonResponse({"error": "Message not found"}, status=404)

        log.status = delivery_status
        log.provider_response = json.dumps(data)
        log.save(update_fields=["status", "provider_response"])

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
