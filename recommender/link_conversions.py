from django.utils import timezone
from datetime import timedelta

from recommender.models import PestRecommendation
from crmapp.models import PurchaseHistory


ATTRIBUTION_WINDOW_DAYS = 7


def link_recommendation_conversions():
    """
    Link PurchaseHistory → PestRecommendation using time-window attribution.
    """

    linked = 0
    window_start = timezone.now() - timedelta(days=ATTRIBUTION_WINDOW_DAYS)

    purchases = PurchaseHistory.objects.filter(
        product__isnull=False,
        purchased_at__gte=window_start
    )

    for p in purchases:

        reco = (
            PestRecommendation.objects.filter(
                customer_id=p.customer_id,                 # ✅ VARCHAR
                recommended_product_id=p.product_id,
                shown_at__lte=p.purchased_at,
                serving_state__in=["served", "exposed", "accepted"]
            )
            .order_by("-shown_at")
            .first()
        )

        if not reco:
            continue

        # Already linked → skip
        if reco.converted_product_id:
            continue

        # 🔗 LINK CONVERSION
        reco.converted_product_id = p.product_id
        reco.converted_at = p.purchased_at
        reco.revenue_amount = p.total_amount
        reco.serving_state = "accepted"
        reco.action = "accepted"

        reco.save(update_fields=[
            "converted_product_id",
            "converted_at",
            "revenue_amount",
            "serving_state",
            "action"
        ])

        linked += 1

    return linked
