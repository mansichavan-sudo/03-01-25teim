from collections import defaultdict
from decimal import Decimal

from recommender.models import PestRecommendation

K = 5


def evaluate_by_recommendation_type():
    """
    Evaluate performance by recommendation_type
    (upsell vs cross_sell vs retention)
    """

    results = {}

    # ----------------------------------
    # STEP 1: Fetch valid recommendations
    # ----------------------------------
    recos = PestRecommendation.objects.exclude(
        recommendation_type__isnull=True
    )

    # ----------------------------------
    # STEP 2: Group by recommendation_type
    # ----------------------------------
    type_groups = defaultdict(list)
    for r in recos:
        type_groups[r.recommendation_type].append(r)

    # ----------------------------------
    # STEP 3: Evaluate each type
    # ----------------------------------
    for reco_type, reco_list in type_groups.items():

        total_recommended = 0
        relevant_count = 0
        click_count = 0
        conversion_count = 0
        revenue_at_k = Decimal("0.0")
        total_revenue = Decimal("0.0")
        customers_with_hit = set()

        # ---- Total revenue (all time)
        for r in reco_list:
            if r.converted_product_id or r.converted_service_id:
                total_revenue += r.revenue_amount or 0

        # ----------------------------------
        # STEP 4: Group by customer
        # ----------------------------------
        customer_groups = defaultdict(list)
        for r in reco_list:
            customer_key = r.canonical_customer_id or r.customer_id
            customer_groups[customer_key].append(r)

        # ----------------------------------
        # STEP 5: Top-K evaluation
        # ----------------------------------
        for customer_key, customer_recos in customer_groups.items():

            top_k = sorted(
                customer_recos,
                key=lambda x: x.final_score or 0,
                reverse=True
            )[:K]

            total_recommended += len(top_k)
            customer_hit = False

            for r in top_k:

                # CTR proxy
                if r.serving_state in ["exposed", "accepted"]:
                    click_count += 1

                # Conversion logic
                is_converted = (
                    r.converted_product_id is not None
                    or r.converted_service_id is not None
                    or r.action == "accepted"
                    or r.serving_state == "accepted"
                )

                if is_converted:
                    relevant_count += 1
                    conversion_count += 1
                    revenue_at_k += r.revenue_amount or 0
                    customer_hit = True

            if customer_hit:
                customers_with_hit.add(customer_key)

        # ----------------------------------
        # STEP 6: Metrics
        # ----------------------------------
        results[reco_type] = {
            "Accuracy (Precision@5)": round(
                relevant_count / total_recommended, 4
            ) if total_recommended else 0,

            "HitRate@5": round(
                len(customers_with_hit) / len(customer_groups), 4
            ) if customer_groups else 0,

            "CTR": round(
                click_count / total_recommended, 4
            ) if total_recommended else 0,

            "ConversionRate": round(
                conversion_count / total_recommended, 4
            ) if total_recommended else 0,

            "Revenue@5": float(revenue_at_k),
            "TotalAttributedRevenue": float(total_revenue),
        }

    return results
