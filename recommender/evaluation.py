from collections import defaultdict
from django.db.models import Q
from recommender.models import PestRecommendation


def evaluate_models(k=5):
    results = {}

    recommendations = PestRecommendation.objects.filter(
        serving_state__in=["served", "exposed", "accepted"]
    )

    models = (
    recommendations
    .exclude(model_source__isnull=True)
    .values_list("model_source", flat=True)
    .distinct()
)


    for model in models:
        recos = recommendations.filter(model_source=model)

        # group by customer
        customer_groups = defaultdict(list)
        for r in recos:
            customer_groups[r.customer_id].append(r)

        total_customers = len(customer_groups)
        if total_customers == 0:
            continue

        hits = 0
        clicks = 0
        conversions = 0
        revenue = 0.0

        for customer, rec_list in customer_groups.items():
            # sort by score
            ranked = sorted(
                rec_list,
                key=lambda x: x.final_score or 0,
                reverse=True
            )

            top_k = ranked[:k]

            # ---- Ranking metrics ----
            if any(r.action == "accepted" for r in top_k):
                hits += 1

            clicks += sum(1 for r in top_k if r.action == "accepted")

            # ---- Conversion metrics (NOT top-k restricted) ----
            for r in rec_list:
                if (
                    r.serving_state == "accepted"
                    and r.converted_product_id is not None
                    and r.revenue_amount
                ):
                    conversions += 1
                    revenue += float(r.revenue_amount)

        results[model] = {
            "Accuracy (Precision@5)": round(clicks / (total_customers * k), 4),
            "HitRate@5": round(hits / total_customers, 4),
            "CTR": round(clicks / (total_customers * k), 4),
            "ConversionRate": round(conversions / total_customers, 4),
            "Revenue@5": round(revenue, 2),
            "TotalAttributedRevenue": round(revenue, 2),
        }

    return results
