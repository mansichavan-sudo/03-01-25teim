# messaging/email.py

import requests
from django.conf import settings
from django.utils import timezone
from recommender.models import MessageDeliveryLog, RecommendationInteraction

def send_email_message(email, subject, message, customer, recommendation):
    payload = {
        "to": email,
        "subject": subject,
        "html": message
    }

    headers = {
        "Authorization": f"Bearer {settings.RAPBOOSTER_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(
        settings.RAPBOOSTER_EMAIL_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    data = resp.json()

    delivery_log = MessageDeliveryLog.objects.create(
        customer=customer,
        recommendation=recommendation,
        channel="email",
        recipient=email,
        message=message,
        provider="rapbooster",
        provider_message_id=data.get("message_id"),
        provider_status=data.get("status"),
        raw_response=data
    )

    RecommendationInteraction.objects.create(
        recommendation=recommendation,
        customer=customer,
        product=recommendation.recommended_product,
        service_id=(
            recommendation.recommended_service.id
            if recommendation.recommended_service else None
        ),
        interaction_type="exposed",
        interaction_channel="email",
        event_time=timezone.now(),
        exposure_id=data.get("message_id"),
        metadata={"delivery_log_id": delivery_log.id}
    )

    recommendation.serving_state = "exposed"
    recommendation.exposure_channel = "email"
    recommendation.exposure_id = data.get("message_id")
    recommendation.shown_at = timezone.now()
    recommendation.save()

    return data.get("status"), data
