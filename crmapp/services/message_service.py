from crmapp.models import (
    customer_details,
    MessageTemplates
)
from recommender.rapbooster_api import (
    send_whatsapp_message,
    send_email_message
)
from recommender.engine import get_recommendations   # your existing logic


def send_recommendation_message(
    customer_id: int,
    template_id: int,
    channel: str,
    custom_subject: str = "",
    custom_body: str = ""
):
    customer = customer_details.objects.get(id=customer_id)
    template = MessageTemplates.objects.get(id=template_id)

    # 1️⃣ Get recommendations
    reco = get_recommendations(customer.customerid)

    # 2️⃣ Render template server-side (SAFE + TRACEABLE)
    body = custom_body or template.render({
        "customer_name": customer.fullname,
        "products": reco.get("products", []),
        "services": reco.get("services", []),
        "intent": reco.get("intent")
    })

    # 3️⃣ Send via channel
    if channel == "whatsapp":
        return send_whatsapp_message(
            phone=customer.primarycontact,
            message=body,
            customer_name=customer.fullname,
            customer=customer,
            template=template
        )

    elif channel == "email":
        return send_email_message(
            email=customer.email,
            subject=custom_subject or template.subject,
            message=body,
            customer_name=customer.fullname,
            customer=customer,
            template=template
        )

    raise ValueError("Invalid channel")
