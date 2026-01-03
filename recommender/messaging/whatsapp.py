# messaging/whatsapp.py

import requests
from django.conf import settings
from django.utils import timezone
from recommender.models import MessageDeliveryLog, RecommendationInteraction

def send_whatsapp_message(phone, message, customer, recommendation):
    payload = {
        "to": phone,
        "type": "text",
        "message": message
    }

    headers = {
        "Authorization": f"Bearer {settings.RAPBOOSTER_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(
        settings.RAPBOOSTER_WHATSAPP_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    data = resp.json()

    # 1️⃣ LOG MESSAGE DELIVERY (PROOF)
    delivery_log = MessageDeliveryLog.objects.create(
        customer=customer,
        recommendation=recommendation,
        channel="whatsapp",
        recipient=phone,
        message=message,
        provider="rapbooster",
        provider_message_id=data.get("message_id"),
        provider_status=data.get("status"),
        raw_response=data
    )

    # 2️⃣ LOG RECOMMENDATION INTERACTION
    RecommendationInteraction.objects.create(
        recommendation=recommendation,
        customer=customer,
        product=recommendation.recommended_product,
        service_id=(
            recommendation.recommended_service.id
            if recommendation.recommended_service else None
        ),
        interaction_type="exposed",
        interaction_channel="whatsapp",
        event_time=timezone.now(),
        exposure_id=data.get("message_id"),
        metadata={"delivery_log_id": delivery_log.id}
    )

    # 3️⃣ UPDATE RECOMMENDATION STATE
    recommendation.serving_state = "exposed"
    recommendation.exposure_channel = "whatsapp"
    recommendation.exposure_id = data.get("message_id")
    recommendation.shown_at = timezone.now()
    recommendation.save(update_fields=[
        "serving_state",
        "exposure_channel",
        "exposure_id",
        "shown_at"
    ])

    return data.get("status"), data
