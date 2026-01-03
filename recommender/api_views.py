# recommender/api_views.py
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from recommender.models import Item
from crmapp.models import customer_details, TaxInvoice, TaxInvoiceItem
import json
import requests

# recommender/api_views.py
import json
import re
import logging
import requests
import os
 
from django.views.decorators.http import require_GET, require_POST
 
from django.contrib.auth.decorators import login_required

from crmapp.models import customer_details, PurchaseHistory, MessageTemplates, SentMessageLog, Product
from .rapbooster_api import send_recommendation_message, send_whatsapp_message, send_email_message


# RAP BOOSTER settings
RAPBOOSTER_API_KEY = "6538c8eff027d41e9151"
RAPBOOSTER_API_URL = "https://rapbooster.in/api/send"


logger = logging.getLogger(__name__)

# --------------------------
# Helper: simple placeholder replace
# --------------------------
def simple_replace(message: str, values: dict):
    if not message:
        return ""
    for k, v in (values or {}).items():
        message = message.replace("{{" + k + "}}", str(v))
    return message

# --------------------------
# GET /api/customers/
# Returns: { customers: [ {customer_id, customer_name, primarycontact, secondarycontact, phone} ] }
# --------------------------
@require_GET
def api_get_customers(request):
    try:
        qs = customer_details.objects.all().values(
            "id", "fullname", "primarycontact", "secondarycontact"
        )
        customers = []
        for c in qs:
            primary = c.get("primarycontact") or ""
            secondary = c.get("secondarycontact") or ""
            phone = primary or secondary or ""
            customers.append({
                "customer_id": c["id"],
                "customer_name": c["fullname"],
                "primarycontact": str(primary) if primary is not None else "",
                "secondarycontact": str(secondary) if secondary is not None else "",
                "phone": str(phone),
            })
        return JsonResponse({"customers": customers})
    except Exception as e:
        logger.exception("api_get_customers error")
        return JsonResponse({"error": str(e)}, status=500)

# --------------------------
# GET /api/customer/<id>/details/
# Returns address and purchase_history: [{product_name, quantity, timestamp}, ...]
# --------------------------
@require_GET
def api_customer_details(request, cid):
    try:
        # Accept both numeric and string ids
        customer = customer_details.objects.filter(id=cid).first()
        if not customer:
            return JsonResponse({"error": "Customer not found"}, status=404)

        # Address fields — adapt to your model field names if needed
        address_parts = []
        for f in ("soldtopartyaddress", "soldtopartycity", "soldtopartystate", "soldtopartypostal"):
            val = getattr(customer, f, None)
            if val:
                address_parts.append(str(val))
        address = ", ".join(address_parts).strip()

        # Purchase history: use PurchaseHistory model (or adjust if you use different name)
        purchases = []
        ph_qs = PurchaseHistory.objects.filter(customer=customer).order_by("-purchased_at")[:200]
        for p in ph_qs:
            # product link: if FK to Product
            prod_name = ""
            try:
                if p.product:
                    prod_name = getattr(p.product, "product_name", "") or ""
                else:
                    prod_name = p.product_name or ""
            except Exception:
                prod_name = p.product_name or ""

            ts = getattr(p, "purchased_at", None)
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else ""

            purchases.append({
                "product_name": prod_name,
                "quantity": float(getattr(p, "quantity", 0) or 0),
                "timestamp": ts_str
            })

        return JsonResponse({
            "customer_id": customer.id,
            "customer_name": getattr(customer, "fullname", ""),
            "address": address,
            "purchase_history": purchases
        })
    except Exception as e:
        logger.exception("api_customer_details error")
        return JsonResponse({"error": str(e)}, status=500)

# --------------------------
# POST /api/send-message/
# Body example:
# {
#   "customer_id": 27,
#   "template_id": 5,            # optional
#   "message_body": "raw text",  # required if template_id missing
#   "send_channel": "whatsapp",  # optional, default whatsapp
#   "contract": "3 Months",      # optional
#   "extra": { "product": "X" }  # optional placeholders
# }
# -------------------------- 
import json
import os
import re
import logging
import requests

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from crmapp.models import customer_details, MessageTemplates
from crmapp.models import SentMessageLog
from recommender.rapbooster_api import (
    send_recommendation_message,
    send_email_message
)

logger = logging.getLogger(__name__)


def simple_replace(text: str, variables: dict) -> str:
    """
    Replace {{var}} placeholders safely
    """
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text


@csrf_exempt
@require_POST
def api_send_message(request):
    # -------------------------------------------------
    # 1. Parse request
    # -------------------------------------------------
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    customer_id = payload.get("customer_id")
    template_id = payload.get("template_id")
    message_body = payload.get("message_body")
    send_channel = (payload.get("send_channel") or "whatsapp").lower()
    contract = payload.get("contract", "")
    extra = payload.get("extra", {}) or {}
    subject = payload.get("subject", "Notification")

    if not customer_id:
        return HttpResponseBadRequest("Missing customer_id")

    # -------------------------------------------------
    # 2. Resolve customer
    # -------------------------------------------------
    try:
        customer = customer_details.objects.get(id=customer_id)
    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    # -------------------------------------------------
    # 3. Resolve template / raw body
    # -------------------------------------------------
    template_obj = None
    raw_body = ""

    if template_id:
        try:
            template_obj = MessageTemplates.objects.get(id=template_id)
            raw_body = template_obj.body or ""
        except MessageTemplates.DoesNotExist:
            return JsonResponse({"error": "Template not found"}, status=404)
    else:
        if not message_body:
            return HttpResponseBadRequest(
                "Either template_id or message_body required"
            )
        raw_body = message_body

    # -------------------------------------------------
    # 4. Build variables
    # -------------------------------------------------
    phone = (
        getattr(customer, "primarycontact", "")
        or getattr(customer, "secondarycontact", "")
        or ""
    )

    email = (
        getattr(customer, "primaryemail", "")
        or getattr(customer, "email", "")
        or ""
    )

    base_vars = {
        "customer_name": getattr(customer, "fullname", "") or "",
        "phone": phone,
        "email": email,
        "contract": contract or ""
    }

    final_vars = {**base_vars, **extra}
    final_message = simple_replace(raw_body, final_vars)

    # -------------------------------------------------
    # 5. WHATSAPP
    # -------------------------------------------------
    if send_channel == "whatsapp":
        if not phone or not re.fullmatch(r"\+?\d{10,15}", phone):
            return JsonResponse(
                {"error": "Invalid or missing phone number"},
                status=400
            )

        try:
            status_code, provider_resp, message_id = send_recommendation_message(
                phone_number=phone,
                message=final_message,
                customer_name=customer.fullname
            )

            success = status_code == 200

        except Exception as e:
            logger.exception("WhatsApp send failed")
            success = False
            provider_resp = {"error": str(e)}
            message_id = None

        # -------------------------------------------------
        # Log
        # -------------------------------------------------
        log = SentMessageLog.objects.create(
            customer=customer,
            template=template_obj,
            recipient=phone,
            channel="whatsapp",
            rendered_body=final_message,
            status="sent" if success else "failed",
            message_id=message_id,
            provider_response=str(provider_resp)
        )

        if not success:
            return JsonResponse(
                {
                    "sent": False,
                    "message_id": log.message_id,
                    "provider_response": provider_resp
                },
                status=400
            )

        return JsonResponse(
            {
                "sent": True,
                "message_id": log.message_id,
                "status": log.status
            }
        )

    # -------------------------------------------------
    # 6. EMAIL
    # -------------------------------------------------
    elif send_channel == "email":
        if not email:
            return JsonResponse(
                {"error": "Customer has no email"},
                status=400
            )

        try:
            provider_resp, message_id = send_email_message(
                email=email,
                subject=subject,
                message=final_message,
                customer_name=customer.fullname
            )

            log = SentMessageLog.objects.create(
                customer=customer,
                template=template_obj,
                recipient=email,
                channel="email",
                rendered_body=final_message,
                status="sent",
                message_id=message_id,
                provider_response=str(provider_resp)
            )

            return JsonResponse(
                {
                    "sent": True,
                    "message_id": log.message_id,
                    "status": log.status
                }
            )

        except Exception as e:
            logger.exception("Email send failed")
            return JsonResponse(
                {"sent": False, "error": str(e)},
                status=500
            )

    # -------------------------------------------------
    # 7. Invalid channel
    # -------------------------------------------------
    return JsonResponse(
        {"error": "Unknown send_channel"},
        status=400
    )


# -------------------------
# Product list for UI
# -------------------------
def product_list(request):
    products = list(Item.objects.order_by("title").values_list("title", flat=True))
    return JsonResponse({"products": products})


# -------------------------
# Customers list for UI
# -------------------------
def customer_list(request):
    # returns list of { customer_id, customer_name }
    qs = customer_details.objects.all().values("id", "fullname")
    data = [{"customer_id": c["id"], "customer_name": c["fullname"]} for c in qs]
    return JsonResponse({"customers": data})


# -------------------------
# Customer detail / phone
# -------------------------
def customer_phone(request, cid):
    try:
        c = customer_details.objects.get(id=cid)
    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found."}, status=404)

    # Try primarycontact then secondarycontact
    phone = None
    if hasattr(c, "primarycontact") and c.primarycontact:
        phone = str(c.primarycontact)
    elif hasattr(c, "secondarycontact") and c.secondarycontact:
        phone = str(c.secondarycontact)

    return JsonResponse({
        "customer_id": c.id,
        "customer_name": getattr(c, "fullname", ""),
        "phone": phone
    })


# -------------------------
# Content-based recommendations
# -------------------------
def get_recommendations(request):
    product_name = request.GET.get("product", "").strip()
    if not product_name:
        return JsonResponse({"error": "Please provide a product name."}, status=400)

    product = Item.objects.filter(title__icontains=product_name).first()
    if not product:
        return JsonResponse({"error": "Product not found."}, status=404)

    similar_products = Item.objects.filter(category=product.category).exclude(id=product.id)[:6]
    return JsonResponse({
        "base_product": product.title,
        "recommended_products": [p.title for p in similar_products]
    })


# -------------------------
# Personalized / Collaborative recommendations (for customer)
# Returns {"recommendations": ["Product A", "Product B", ...]}
# -------------------------
def user_recommendations(request, customer_id):
    invoices = TaxInvoice.objects.filter(customer_id=customer_id)
    if not invoices.exists():
        return JsonResponse({"recommendations": []})

    # products this customer purchased
    purchased_product_ids = TaxInvoiceItem.objects.filter(invoice__in=invoices).values_list("product_id", flat=True)

    # Find other invoice items co-purchased by other customers (excluding customer's products)
    co_purchased = (TaxInvoiceItem.objects
                    .exclude(product_id__in=purchased_product_ids)
                    .values("product_id")
                    .annotate(cnt=Count("product_id"))
                    .order_by("-cnt")[:8])

    # Map product_id -> product title using Item model (best effort)
    product_titles = []
    for entry in co_purchased:
        pid = entry["product_id"]
        item = Item.objects.filter(id=pid).first()
        if item:
            product_titles.append(item.title)
        else:
            # fallback to product_id string if no Item row
            product_titles.append(f"Product-{pid}")

    return JsonResponse({"recommendations": product_titles})


# -------------------------
# Upsell suggestions (by product_id)
# -------------------------
def upsell_recommendations_api(request, product_id):
    try:
        base = Item.objects.get(id=product_id)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Product not found.'}, status=404)

    # Suggest higher-tier (recent) products in same category
    upsells = Item.objects.filter(category=base.category).exclude(id=base.id).order_by("-created_at")[:4]
    return JsonResponse({"product": base.title, "upsell_suggestions": [p.title for p in upsells]})


# -------------------------
# Cross-sell suggestions (by customer)
# -------------------------
def cross_sell_recommendations_api(request, customer_id):
    invoices = TaxInvoice.objects.filter(customer_id=customer_id)
    if not invoices.exists():
        return JsonResponse({'cross_sell_suggestions': []})

    purchased_product_ids = TaxInvoiceItem.objects.filter(invoice__in=invoices).values_list("product_id", flat=True)

    co_purchased = (TaxInvoiceItem.objects
                    .exclude(product_id__in=purchased_product_ids)
                    .values("product_id")
                    .annotate(cnt=Count("product_id"))
                    .order_by("-cnt")[:6])

    titles = []
    for entry in co_purchased:
        pid = entry["product_id"]
        item = Item.objects.filter(id=pid).first()
        if item:
            titles.append(item.title)
        else:
            titles.append(f"Product-{pid}")

    return JsonResponse({"cross_sell_suggestions": titles})


# -------------------------
# Message generation (simple)
# -------------------------
@csrf_exempt
def generate_message_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    try:
        data = json.loads(request.body)
        customer = data.get("customer_name")
        base = data.get("base_product")
        recommended = data.get("recommended_product")
        rec_type = data.get("recommendation_type", "recommendation")
        if not all([customer, base, recommended]):
            return JsonResponse({"error": "Missing required fields."}, status=400)

        message = f"Hello {customer}, since you had {base}, we recommend {recommended}. ({rec_type})"
        return JsonResponse({"message": message})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------
# Send message via RAP Booster
# -------------------------
@csrf_exempt
def send_message_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        customer_name = data.get("customer_name")
        customer_number = data.get("customer_number")
        message = data.get("message")

        if not all([customer_name, customer_number, message]):
            return JsonResponse({"error": "customer_name, customer_number, message required."}, status=400)

        payload = {
            "apikey": RAPBOOSTER_API_KEY,
            "mobile": str(customer_number),
            "msg": message
        }

        response = requests.post(RAPBOOSTER_API_URL, data=payload, timeout=15)
        try:
            result = response.json() if response.text else {"status": "no response"}
        except:
            result = {"status": "invalid json from provider", "text": response.text}

        if response.status_code == 200:
            return JsonResponse({"status": "success", "response": result})
        else:
            return JsonResponse({"status": "failed", "response": result}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# recommender/views_api.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .ml.ml_service import get_recommendations


@csrf_exempt
def api_get_recommendations(request, customer_id):
    """
    Main production API for recommendation system.
    Input: customer_id (int)
    Output: JSON response with recommended products.
    """

    try:
        customer_id = int(customer_id)
    except:
        return JsonResponse({
            "status": "error",
            "message": "Invalid customer_id."
        }, status=400)

    # Call ML engine
    result = get_recommendations(customer_id)

    # If engine failed
    if result.get("status") == "error":
        return JsonResponse(result, status=500)

    # Successful output
    return JsonResponse({
        "status": "success",
        "customer_id": customer_id,
        "recommendations": result.get("recommendations", []),
        "message": result.get("message", "")
    }, status=200)


from django.views.decorators.http import require_GET

from django.http import JsonResponse
from crmapp.models import SentMessageLog


def api_message_status(request, message_id):

    try:
        msg = SentMessageLog.objects.get(message_id=message_id)
    except SentMessageLog.DoesNotExist:
        return JsonResponse({
            "error": "Message not found"
        }, status=404)

    return JsonResponse({
        "message_id": msg.message_id,
        "status": msg.status.upper(),
        "channel": msg.channel
    })


import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from crmapp.models import SentMessageLog


@csrf_exempt
def rapbooster_webhook(request):

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message_id = payload.get("message_id")
    status = payload.get("status")

    if not message_id or not status:
        return JsonResponse({"error": "message_id and status required"}, status=400)

    try:
        msg = SentMessageLog.objects.get(message_id=message_id)
    except SentMessageLog.DoesNotExist:
        return JsonResponse({"error": "Message not found"}, status=404)

    # Normalize statuses
    STATUS_MAP = {
        "sent": "sent",
        "delivered": "delivered",
        "read": "read",
        "failed": "failed",
        "bounced": "failed"
    }

    normalized_status = STATUS_MAP.get(status.lower(), status.lower())

    msg.status = normalized_status
    msg.provider_response = payload
    msg.save(update_fields=["status", "provider_response"])

    return JsonResponse({"ok": True})


import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from crmapp.models import SentMessageLog, MessageTemplates, customer_details
from recommender.rapbooster_api import (
    send_whatsapp_message,
    send_email_message
)

@csrf_exempt
def send_message_api(request):
    if request.method != "POST":
        return JsonResponse({"sent": False, "error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"sent": False, "error": "Invalid JSON"}, status=400)

    # ------------------ REQUIRED FIELDS ------------------
    customer_id = data.get("customer_id")
    template_id = data.get("template_id")
    rendered_message = data.get("rendered_message") or data.get("message_body")
    subject = data.get("subject", "")
    send_channel = data.get("send_channel", data.get("channel", "whatsapp")).lower()

    if not customer_id or not rendered_message:
        return JsonResponse({"sent": False, "error": "Missing required fields"}, status=400)

    if send_channel not in ["whatsapp", "email"]:
        return JsonResponse({"sent": False, "error": "Invalid channel"}, status=400)

    # ------------------ FETCH DB OBJECTS ------------------
    try:
        customer = customer_details.objects.get(id=customer_id)
    except customer_details.DoesNotExist:
        return JsonResponse({"sent": False, "error": "Customer not found"}, status=404)

    template = None
    if template_id:
        template = MessageTemplates.objects.filter(id=template_id).first()

    recipient = (
        customer.primarycontact
        if send_channel == "whatsapp"
        else customer.primaryemail
    )

    if not recipient:
        return JsonResponse(
            {"sent": False, "error": f"No recipient for {send_channel}"},
            status=400
        )

    # ------------------ CREATE LOG FIRST ------------------
    log = SentMessageLog.objects.create(
        template=template,
        customer=customer,
        customer_name=customer.fullname,
        recipient=recipient,
        channel=send_channel,
        rendered_subject=subject,
        rendered_body=rendered_message,
        status="queued",
    )

    # ------------------ SEND MESSAGE ------------------
    try:
        if send_channel == "whatsapp":
            status, response, provider_id = send_whatsapp_message(
                phone=recipient,
                message=rendered_message,
                customer_name=customer.fullname,
                customer=customer,
                template=template,
            )
        else:
            status, response, provider_id = send_email_message(
                email=recipient,
                subject=subject,
                message=rendered_message,
                customer_name=customer.fullname,
                customer=customer,
                template=template,
            )
    except Exception as e:
        log.status = "failed"
        log.provider_response = str(e)
        log.save(update_fields=["status", "provider_response"])
        return JsonResponse({"sent": False, "error": "Provider error"}, status=500)

    # ------------------ UPDATE LOG ------------------
    log.status = status
    log.provider_response = json.dumps(response)
    log.message_id = provider_id or f"rb_{log.id}"
    log.save()

    return JsonResponse({
        "sent": True,
        "status": status,
        "message_id": log.message_id,
    })

@csrf_exempt
def message_status_api(request, message_id):
    try:
        log = SentMessageLog.objects.get(message_id=message_id)

        return JsonResponse({
            "success": True,
            "message_id": message_id,
            "status": log.status,
            "delivery_status": log.delivery_status or log.status,
            "updated_at": log.updated_at
        })

    except SentMessageLog.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Message not found"
        }, status=404)
