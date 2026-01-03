# recommender/pipeline_scoring.py

from django.utils import timezone
from datetime import timedelta
from recommender.models import PestRecommendation


INTENT_WEIGHTS = {
    "upsell": 1.0,
    "crosssell": 0.7,
    "retention": 0.5,
    "reactivation": 0.6
}

CHANNEL_WEIGHTS = {
    "whatsapp": 1.0,
    "app": 0.9,
    "crm": 0.6,
    "call": 0.5
}


def compute_recency_weight(created_at):
    if not created_at:
        return 0.3

    days_old = (timezone.now() - created_at).days

    if days_old <= 1:
        return 1.0
    if days_old <= 3:
        return 0.8
    if days_old <= 7:
        return 0.6
    return 0.4


def score_pipeline_recommendations():
    recos = PestRecommendation.objects.filter(
        model_source="pipeline",
        is_active=True
    )

    updated = 0

    for r in recos:
        confidence = float(r.confidence_score or 0)
        intent_weight = INTENT_WEIGHTS.get(r.business_intent, 0.5)
        recency_weight = compute_recency_weight(r.created_at)
        channel_weight = CHANNEL_WEIGHTS.get(r.exposure_channel, 0.6)
        priority_weight = max(0.1, min(1.0, 1 - (r.priority or 100) / 200))

        final_score = (
            confidence * 0.4
            + intent_weight * 0.2
            + recency_weight * 0.2
            + channel_weight * 0.1
            + priority_weight * 0.1
        )

        r.final_score = round(final_score, 3)
        r.save(update_fields=["final_score"])
        updated += 1

    return updated
