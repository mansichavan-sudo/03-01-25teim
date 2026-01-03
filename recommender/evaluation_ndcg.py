import math
from collections import defaultdict

from recommender.models import PestRecommendation

K = 5


# -----------------------------
# DCG calculation
# -----------------------------
def dcg(relevances):
    """
    relevances = list of 0/1 relevance values
    """
    score = 0.0
    for i, rel in enumerate(relevances):
        score += rel / math.log2(i + 2)
    return score


# -----------------------------
# NDCG calculation
# -----------------------------
def ndcg_at_k(relevances, k=5):
    if not relevances:
        return 0.0

    relevances = relevances[:k]
    ideal = sorted(relevances, reverse=True)

    dcg_val = dcg(relevances)
    idcg_val = dcg(ideal)

    return dcg_val / idcg_val if idcg_val > 0 else 0.0


# -----------------------------
# Main Evaluation
# -----------------------------
def evaluate_ndcg(model_source=None):
    """
    Compute NDCG@5
    If model_source is provided:
        'rule_based', 'pipeline', etc
    """

    qs = PestRecommendation.objects.all()

    if model_source:
        qs = qs.filter(model_source=model_source)

    # Group by customer
    customer_groups = defaultdict(list)
    for r in qs:
        customer_key = r.canonical_customer_id or r.customer_id
        customer_groups[customer_key].append(r)

    ndcg_scores = []

    for customer_key, recos in customer_groups.items():

        # Sort by model ranking
        ranked = sorted(
            recos,
            key=lambda x: x.final_score or 0,
            reverse=True
        )[:K]

        # Build relevance list
        relevances = []
        for r in ranked:
            is_relevant = (
                r.converted_product_id is not None
                or r.converted_service_id is not None
                or r.action == "accepted"
                or r.serving_state == "accepted"
            )
            relevances.append(1 if is_relevant else 0)

        if sum(relevances) > 0:
            ndcg_scores.append(ndcg_at_k(relevances, K))

    # Average NDCG
    return round(sum(ndcg_scores) / len(ndcg_scores), 4) if ndcg_scores else 0.0
