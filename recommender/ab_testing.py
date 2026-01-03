from collections import defaultdict
from django.db.models import Count, Sum, Q

from recommender.models import PestRecommendation


def run_ab_test():
    """
    A/B test using experiment_group
    A = control (rule_based)
    B = treatment (pipeline)
    """

    results = {}

    # Only exposed recommendations
    qs = PestRecommendation.objects.filter(
        serving_state__in=["exposed", "accepted", "converted"]
    )

    # Group by experiment
    for group in ["A", "B"]:

        group_qs = qs.filter(experiment_group=group)

        exposed = group_qs.count()

        clicked = group_qs.filter(
            Q(action="accepted") |
            Q(serving_state="accepted")
        ).count()

        converted = group_qs.filter(
            Q(converted_product_id__isnull=False) |
            Q(converted_service_id__isnull=False)
        ).count()

        revenue = (
            group_qs.filter(
                Q(converted_product_id__isnull=False) |
                Q(converted_service_id__isnull=False)
            )
            .aggregate(total=Sum("revenue_amount"))
            .get("total") or 0
        )

        results[group] = {
            "Exposed": exposed,
            "CTR": round(clicked / exposed, 4) if exposed else 0,
            "ConversionRate": round(converted / exposed, 4) if exposed else 0,
            "RevenuePerExposure": round(float(revenue) / exposed, 2) if exposed else 0,
            "TotalRevenue": float(revenue),
        }

    # -----------------------------
    # Lift Calculation (B vs A)
    # -----------------------------
    if results["A"]["Exposed"] > 0:

        results["Lift"] = {
            "CTR_Lift_%": round(
                ((results["B"]["CTR"] - results["A"]["CTR"]) / results["A"]["CTR"]) * 100,
                2
            ) if results["A"]["CTR"] > 0 else 0,

            "Conversion_Lift_%": round(
                ((results["B"]["ConversionRate"] - results["A"]["ConversionRate"]) /
                 results["A"]["ConversionRate"]) * 100,
                2
            ) if results["A"]["ConversionRate"] > 0 else 0,

            "Revenue_Lift_%": round(
                ((results["B"]["RevenuePerExposure"] - results["A"]["RevenuePerExposure"]) /
                 results["A"]["RevenuePerExposure"]) * 100,
                2
            ) if results["A"]["RevenuePerExposure"] > 0 else 0,
        }

    return results
