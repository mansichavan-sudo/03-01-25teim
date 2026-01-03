from recommender.models import PestRecommendation


def get_customer_recommendations(customer_id: int):
    """
    Returns recommended products & services for a customer
    """

    recos = PestRecommendation.objects.filter(
        customer_id=customer_id,
        is_active=True
    )

    products = []
    services = []

    for r in recos:
        if r.recommendation_type == "product" and r.recommended_product:
            products.append(r.recommended_product.name)

        if r.recommendation_type == "service" and r.recommended_service:
            services.append(r.recommended_service.name)

    return {
        "products": products,
        "services": services
    }
