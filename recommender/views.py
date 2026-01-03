# recommender/views.py

from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from .rapbooster_api import send_email_message 
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json
import pickle
import os
import requests
import re
from .rapbooster_api import send_whatsapp_message, send_email_message, send_recommendation_message
from django.shortcuts import get_object_or_404
# Models
from crmapp.models import MessageTemplates, Product, customer_details ,PurchaseHistory,ServiceProduct,invoice 
from .models import Item, Rating, PestRecommendation
from django.http import HttpResponse
from openpyxl import Workbook
import csv
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from crmapp.models import SentMessageLog
from django.db import connection
from .engine import get_recommendations
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
import json
import os
import re
import requests
from django.shortcuts import get_object_or_404
from crmapp.models import customer_details, MessageTemplates, SentMessageLog , CustomerContract
from .ml_service import get_recommendations_for_customer
import traceback
from recommender.engine import cf_get_recommendations

 




# Recommender Engine
from .recommender_engine import (
    get_content_based_recommendations,
    get_collaborative_recommendations,
    get_upsell_recommendations,
    get_crosssell_recommendations,
    generate_recommendations_for_user,
    get_user_based_recommendations
)

from .utils import send_recommendation_message
import joblib


# -------------------------------------------------------------
#  Load ML Models
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_CF = os.path.join(BASE_DIR, "trained_models", "recommender_model.pkl")
MODEL_HYBRID = os.path.join(BASE_DIR, "trained_models", "hybrid_model.pkl")

cf_model = joblib.load(MODEL_CF) if os.path.exists(MODEL_CF) else None
hybrid_model = joblib.load(MODEL_HYBRID) if os.path.exists(MODEL_HYBRID) else None


# Helper: Render placeholders
def render_template(text, data):
    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", lambda m: str(data.get(m.group(1), "")), text or "")

# ============================================================
# 1️⃣ RECOMMENDATION UI
# ============================================================
@login_required
@ensure_csrf_cookie
def recommendation_ui(request):
    """
    Renders the single-page UI merging Content-Based + Personalized into one.
    Template will populate customers, templates; the rest is done with AJAX.
    """
    # Load customers minimally (id + fullname) for dropdowns
    customers = customer_details.objects.all().values("id", "fullname")
    # Load templates active by default; when customer selected front-end will pick up customer-specific filtering by reloading templates if needed
    templates = MessageTemplates.objects.filter(is_active=True).order_by("category", "message_type")
    return render(request, 'recommender/recommendations_ui.html', {
        'templates': templates,
        'customers': customers,
    })

# ============================================================
# 2️⃣ CONTENT-BASED RECOMMENDATIONS (product → product)
# ============================================================
def recommendations_view(request):
    product_name = request.GET.get('product')
    if not product_name:
        return JsonResponse({'error': 'Please provide a product name.'}, status=400)
    try:
        results = get_content_based_recommendations(product_name)
        return JsonResponse({'recommended_products': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ============================================================
# 3️⃣ COLLABORATIVE FILTERING (customer → customer)
# ============================================================
def collaborative_view(request, customer_id):
    try:
        results = get_collaborative_recommendations(customer_id)
        return JsonResponse({'similar_customers': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
 

from django.db.models import Count,Avg

from django.http import JsonResponse


from django.http import JsonResponse
from django.db.models import Avg, Count, DecimalField
from django.db.models.functions import Coalesce
from .recommender_engine import get_upsell_recommendations
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.db.models.functions import Coalesce
from decimal import Decimal
from crmapp.models import Product, ServiceProduct


def popular_products_api(request, customer_id):
    products = Product.objects.annotate(
        sales=Count('purchasehistory'),
        avg_price=Coalesce(
            Avg('serviceproduct__price'),
            Decimal('0.00')
        )
    ).order_by('-sales')[:5]

    result = [
        {
            "product_name": p.product_name,
            "average_price": float(round(p.avg_price, 2)),
            "reason": "Popular product"
        }
        for p in products
    ]

    return JsonResponse(result, safe=False)


# -------------------------
# Upsell Suggestions API
# ------------------------- 
from django.http import JsonResponse
from django.db.models import Max
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.db.models import Max, Avg, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.db.models import Avg, Max, DecimalField
from django.db.models.functions import Coalesce
from crmapp.models import customer_details, ServiceProduct
from recommender.models import PestRecommendation


from django.http import JsonResponse
from recommender.models import PestRecommendation
 

def _serialize_recommendations(qs):
    products = []
    services = []

    for r in qs:
        if r.reco_channel == "product" and r.recommended_product:
            products.append({
                "product_id": r.recommended_product.id,
                "product_name": r.recommended_product.product_name,
                "confidence": round(r.confidence, 3),
            })

        if r.reco_channel == "service" and r.recommended_service:
            services.append({
                "service_id": r.recommended_service.id,
                "service_name": r.recommended_service.service_name,
                "confidence": round(r.confidence, 3),
            })

    return {
        "products": products,
        "services": services,
    }


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from recommender.models import PestRecommendation
from crmapp.models import customer_details


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
 
import logging

logger = logging.getLogger(__name__)


def _safe_response(products, services):
    """
    Guarantees frontend-safe structure
    """
    return {
        "products": products if isinstance(products, list) else [],
        "services": services if isinstance(services, list) else [],
    }


def upsell_view(request, customer_id):

    if customer_id == "ALL":
        customer_pk = "ALL"
    else:
        customer = get_object_or_404(customer_details, customerid=customer_id)
        customer_pk = customer.id

    products, services = get_recommendations(customer_pk, "upsell")

    return JsonResponse({
        "status": "success",
        "intent": "upsell",
        "scope": "global" if customer_pk == "ALL" else "customer",
        "products": products,
        "services": services
    })

def crosssell_view(request, customer_id):

    if customer_id == "ALL":
        customer_pk = "ALL"
    else:
        customer = get_object_or_404(customer_details, customerid=customer_id)
        customer_pk = customer.id

    products, services = get_recommendations(customer_pk, "crosssell")

    return JsonResponse({
        "status": "success",
        "intent": "crosssell",
        "scope": "global" if customer_pk == "ALL" else "customer",
        "products": products,
        "services": services
    })

# ============================================================
# 6️⃣ FINAL DASHBOARD TABLE (CRM)
# ============================================================ 
from django.core.paginator import Paginator
from django.db import connection
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db import connection
from django.shortcuts import render

from django.core.paginator import Paginator
from django.db import connection
from django.shortcuts import render

def recommendation_dashboard(request):
    filter_type = (request.GET.get("type") or "").strip().lower()
    algo_button = (request.GET.get("algo") or "").strip().lower()
    search = (request.GET.get("search") or "").strip()

    algo_map = {
        "rule-based": "rule_based",
        "content-based": "content",
        "collaborative": "collaborative",
        "demographic": "demographic",
        "hybrid": "hybrid",
    }
    algo = algo_map.get(algo_button)
    params = []

    # -------------------------------
    # SUBQUERY: rank product & service separately
    # -------------------------------
    subquery = """
        SELECT *
        FROM (
            SELECT
                pr.customer_fk,
                pr.recommended_product_id,
                pr.recommended_service_id,
                pr.reco_channel,
                pr.business_intent,
                pr.algorithm_strategy,
                pr.confidence_score,
                ROW_NUMBER() OVER (
                    PARTITION BY pr.customer_fk, pr.reco_channel
                    ORDER BY pr.confidence_score DESC
                ) AS rn
            FROM pest_recommendations pr
            WHERE pr.is_active = 1
    """

    if filter_type:
        subquery += " AND pr.business_intent = %s"
        params.append(filter_type)

    if algo:
        subquery += " AND pr.algorithm_strategy = %s"
        params.append(algo)

    subquery += ") ranked WHERE rn = 1"

    # -------------------------------
    # MAIN QUERY: merge product + service into one row per customer
    # -------------------------------
    sql = f"""
        SELECT
            pr.customer_fk,
            c.fullname,
            c.primarycontact,
            c.primaryemail,
            CONCAT_WS(', ',
                c.soldtopartyaddress,
                c.soldtopartycity,
                c.soldtopartystate,
                c.soldtopartypostal
            ) AS address,
            lp.product_name AS purchase_product,
            sp.quantity,
            sp.price,
            sm.service_date,
            MAX(CASE WHEN pr.reco_channel = 'product' THEN rp.product_name END) AS recommended_product,
            MAX(CASE WHEN pr.reco_channel = 'service' THEN sc.service_name END) AS recommended_service,
            COALESCE(MAX(rp.category), MAX(sc.service_category)) AS category,
            MAX(pr.business_intent) AS business_intent,
            MAX(pr.algorithm_strategy) AS algorithm_strategy,
            MAX(pr.confidence_score) AS confidence_score
        FROM ({subquery}) pr
        LEFT JOIN crmapp_customer_details c ON c.id = pr.customer_fk
        LEFT JOIN crmapp_service_management sm ON sm.customer_id = c.id
        LEFT JOIN crmapp_serviceproduct sp ON sp.service_id = sm.id
        LEFT JOIN crmapp_product lp ON lp.product_id = sp.product_id
        LEFT JOIN crmapp_product rp ON rp.product_id = pr.recommended_product_id
        LEFT JOIN service_catalog sc ON sc.service_id = pr.recommended_service_id
    """

    if search:
        sql += """
            WHERE (
                c.fullname LIKE %s
                OR rp.product_name LIKE %s
                OR sc.service_name LIKE %s
            )
        """
        like = f"%{search}%"
        params.extend([like, like, like])

    sql += " GROUP BY pr.customer_fk, c.fullname, c.primarycontact, c.primaryemail, address, lp.product_name, sp.quantity, sp.price, sm.service_date"
    sql += " ORDER BY confidence_score DESC, sm.service_date DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    recommendations = [{
        "customer_id": r[0],
        "customer_name": r[1],
        "phone": r[2],
        "email": r[3],
        "address": r[4] or "—",
        "purchase_product": r[5] or "—",
        "quantity": r[6] or "—",
        "price": float(r[7]) if r[7] else "—",
        "purchase_date": r[8],
        "recommended_product": r[9] or "—",
        "recommended_service": r[10] or "—",
        "category": r[11] or "—",
        "business_intent": r[12] or "—",
        "algorithm_strategy": r[13] or "—",
        "confidence_score": float(r[14]) if r[14] else 0,
    } for r in rows]

    paginator = Paginator(recommendations, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "recommender/recommendation_dashboard.html",
        {
            "page_obj": page_obj,
            "filter_type": filter_type,
            "algo": algo_button,
            "search": search,
        }
    )


# ============================================================
# 7️⃣ GET ALL PRODUCTS
# ============================================================
def get_all_products(request):
    try:
        products = list(Product.objects.values_list("product_name", flat=True))
        return JsonResponse({'products': products})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


import logging
logger = logging.getLogger(__name__)

@login_required
@require_GET
def api_ai_personalized(request, customer_id):
    """
    Returns AI personalized recommendations for a customer.
    URL sends REAL PK <int:customer_id>.
    """

    # ----------------------------------------------------------------------
    # 1. Validate & fetch customer (using REAL primary key)
    # ----------------------------------------------------------------------
    try:
        customer_id = int(customer_id)
    except ValueError:
        return JsonResponse({"error": "Invalid customer ID"}, status=400)

    customer = get_object_or_404(customer_details, id=customer_id)

    # ----------------------------------------------------------------------
    # 2. Generate recommendations
    # ----------------------------------------------------------------------
    try:
        recs = generate_recommendations_for_user(
            customer_id=customer_id,
            top_n=10
        )
    except Exception as e:
        logger.error(f"[AI] Recommendation generation failed for customer {customer_id}: {e}")
        recs = []

    # ----------------------------------------------------------------------
    # 3. Normalize recommendation objects → clean JSON list
    # ----------------------------------------------------------------------
    final_recs = []

    for r in recs:
        try:
            product_id = (
                getattr(r, "product_id", None)
                or getattr(r, "id", None)
            )

            title = (
                getattr(r, "title", None)
                or getattr(r, "product_name", None)
                or "Unknown Item"
            )

            final_recs.append({
                "product_id": product_id,
                "product": title,   # UI friendly
                "title": title,
                "category": getattr(r, "category", None),
                "tags": getattr(r, "tags", None),
                "confidence_score": getattr(r, "score", None),
     })

        except Exception as e:
            logger.warning(f"[AI] Failed to normalize recommendation: {e}")
            continue

    # ----------------------------------------------------------------------
    # 4. JSON Response
    # ----------------------------------------------------------------------
    return JsonResponse({
        "customer_id": customer.id,
        "customer_name": customer.fullname,
        "recommendations": final_recs,
    })

# ============================================================
# 9️⃣ AUTOMATIC MESSAGE GENERATION + SEND
# ============================================================
@csrf_exempt
def generate_message(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)

        customer = data.get("customer_name")
        base = data.get("base_product")
        rec = data.get("recommended_product")
        rec_type = data.get("recommendation_type")
        phone_number = data.get("phone_number")

        if not all([customer, base, rec, rec_type, phone_number]):
            return JsonResponse({"error": "Missing fields"}, status=400)

        message = (
            f"Hello {customer}, we recommend trying our {rec} as a perfect "
            f"{rec_type.lower()} option with your {base}. "
            f"It ensures better pest control results! 🌾🛡️"
        )

        from .rapbooster_api import send_recommendation_message

        status_code, api_response = send_recommendation_message(
            phone_number=phone_number,
            message=message,
            customer_name=customer
        )

        return JsonResponse({
            "customer": customer,
            "phone": phone_number,
            "message": message,
            "status": "sent" if status_code == 200 else "failed",
            "api_response": api_response
        })

    except Exception as e:
        logger.error(f"Message generation error: {e}")
        return JsonResponse({"error": str(e)}, status=500)



# ============================================================
# 🔟 RAP BOOSTER MESSAGE SENDER (FINAL FIXED VERSION)
# ============================================================
@csrf_exempt
def send_message_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        # ENV fallback
        RAPBOOSTER_API_KEY = os.getenv("RAPBOOSTER_API_KEY")
        if not RAPBOOSTER_API_KEY:
            RAPBOOSTER_API_KEY = "6538c8eff027d41e9151"  # Safe fallback

        RAPBOOSTER_SEND_URL = "https://rapbooster.in/api/v1/sendMessage"

        data = json.loads(request.body)
        template_id = data.get("template_id")
        customer_id = data.get("customer_id")

        if not template_id or not customer_id:
            return JsonResponse({"error": "template_id and customer_id are required"}, status=400)

        template = MessageTemplates.objects.get(id=template_id)
        customer = customer_details.objects.get(id=customer_id)

        phone = str(customer.primarycontact).strip()

        # Phone validation: 10–15 digits
        if not re.fullmatch(r"\+?\d{10,15}", phone):
            return JsonResponse({"error": "Invalid phone number format"}, status=400)

        # Render the template body
        rendered_body = render_template(template.body, {
            "customer_name": customer.fullname,
            "recommended_product": data.get("recommended_product", "")
        })

        payload = {
            "apikey": RAPBOOSTER_API_KEY,
            "phone": phone,
            "message": rendered_body
        }

        response = requests.post(RAPBOOSTER_SEND_URL, json=payload, timeout=10)

        try:
            resp_json = response.json()
        except:
            resp_json = {}

        # Success check
        success = response.status_code == 200 and resp_json.get("status") == "success"

        SentMessageLog.objects.create(
            template=template,
            recipient=phone,
            channel=template.message_type,
            rendered_body=rendered_body,
            status="success" if success else "failed",
            provider_response=response.text,
        )

        if success:
            return JsonResponse({
                "status": "success",
                "message_id": resp_json.get("message_id"),
                "phone": resp_json.get("phone")
            })

        return JsonResponse({
            "status": "failed",
            "error": resp_json.get("error", "Unknown error"),
            "http_status": response.status_code
        }, status=500)

    except MessageTemplates.DoesNotExist:
        return JsonResponse({"error": "Template not found"}, status=404)

    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except requests.RequestException as e:
        logger.error(f"RapBooster error: {e}")
        return JsonResponse({"error": "Network error contacting RapBooster"}, status=500)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)
    


# ------------------------------------------------------------
# API → Load customer details, purchase history & AI product
# ------------------------------------------------------------ 

# ============================================================
# 1️⃣1️⃣ FIXED – GET CUSTOMER FULL DATA
# ============================================================ 
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from crmapp.models import customer_details, PurchaseHistory

def get_customer_data(request, customer_id):

    customer = get_object_or_404(customer_details, customerid=customer_id)

    # phone
    phone = customer.primarycontact or customer.secondarycontact or ""

    # address formatting
    address = f"{customer.soldtopartyaddress}, {customer.soldtopartycity}, {customer.soldtopartystate}, {customer.soldtopartypostal}"

    # purchase history
    purchases = PurchaseHistory.objects.filter(customer_id=customer_id).order_by("-purchased_at")

    purchase_rows = []
    last_purchase_date = None
    last_purchase_item = None

    for p in purchases:

        if last_purchase_date is None:
            last_purchase_date = p.purchased_at.strftime("%Y-%m-%d %H:%M")
            last_purchase_item = p.product_name

        purchase_rows.append({
            "product_name": p.product_name,
            "quantity": float(p.quantity),
            "date": p.purchased_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({
        "customer": {
            "id": customer.customerid,
            "name": customer.fullname,
            "phone": phone,
            "address": address,
            "last_purchase": last_purchase_date,
            "last_purchase_item": last_purchase_item,
        },
        "purchase_history": purchase_rows,
        "recommendations": []
    })

# ============================================================
# 1️⃣1️⃣ CUSTOMER RECOMMENDATIONS API
# ============================================================  
def customer_recommendations_api(request, customer_id):
    try:
        # Get list of recommended products
        recommendations = get_user_based_recommendations(customer_id)

        # Select the top recommendation (or fallback)
        if recommendations and len(recommendations) > 0:
            top_recommendation = recommendations[0]
        else:
            top_recommendation = "General Pest Control"  # fallback

        # Send response in UI expected format
        return JsonResponse({
            "customer_id": customer_id,
            "recommended_product": top_recommendation
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



# api/customers/

# ----------- FETCH ALL CUSTOMERS ----------- 
from crmapp.models import customer_details, PurchaseHistory
from django.db.models import Max
def get_all_customers(request):

    customers = list(customer_details.objects.all().values(
        "id",
        "customerid",
        "fullname",
        "primarycontact",
        "soldtopartyaddress",
        "soldtopartycity",
        "soldtopartystate",
        "soldtopartypostal",
    ))

    # MUST return a list
    return JsonResponse(customers, safe=False)

def customer_address(request, customerid):
    try:
        customer = customer_details.objects.filter(customerid=customerid).values().first()

        if not customer:
            return JsonResponse({"error": "Customer not found"}, status=404)

        return JsonResponse({
            "fullname": customer.get("fullname"),
            "address": customer.get("soldtopartyaddress"),
            "city": customer.get("soldtopartycity"),
            "state": customer.get("soldtopartystate"),
            "postal": customer.get("soldtopartypostal"),
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def purchase_history(request, customerid):
    try:
        history = list(
            PurchaseHistory.objects.filter(customerid=customerid).values()
        )
        return JsonResponse({"history": history}, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


# ----------------------------
# 4. Recommendation API
# ----------------------------

# Load models on server start
BASE = os.path.dirname(os.path.abspath(__file__))

try:
    cf_model_path = os.path.join(BASE, "..", "recommender", "trained_models", "recommender_model.pkl")
    hybrid_model_path = os.path.join(BASE, "..", "recommender", "trained_models", "hybrid_recommender.pkl")

    CF_MODEL = joblib.load(cf_model_path)
    HYBRID_MODEL = joblib.load(hybrid_model_path)

    print("✅ Recommendation Models Loaded")

except Exception as e:
    print("❌ ERROR loading models:", e)
    CF_MODEL = None
    HYBRID_MODEL = None

import joblib
def generate_recommendations(customerid):
    """Runs CF + Hybrid models and returns unique results"""

    results = {}

    # ---- CF Model ----
    if CF_MODEL:
        try:
            results["cf"] = CF_MODEL.get(customerid, [])[:10]
        except:
            results["cf"] = []
    else:
        results["cf"] = []

    # ---- Hybrid Model ----
    if HYBRID_MODEL:
        try:
            results["hybrid"] = HYBRID_MODEL.get(customerid, [])[:10]
        except:
            results["hybrid"] = []
    else:
        results["hybrid"] = []

    # ---- Combine & Make Unique ----
    combined = list(dict.fromkeys(results["cf"] + results["hybrid"]))

    return {
        "cf_recommendations": results["cf"],
        "hybrid_recommendations": results["hybrid"],
        "final_recommendations": combined
    }

 

from django.db.models import Max
from crmapp.models import customer_details, PurchaseHistory

@login_required
@require_GET  
def api_get_customers(request):

    customers = list(customer_details.objects.all().values(
        "id",                      # real PK
        "customerid",              # string code
        "fullname",
        "primarycontact",
        "soldtopartyaddress",
        "soldtopartycity",
        "soldtopartystate",
        "soldtopartypostal",
    ))

    # Get last purchase using customer_ref (REAL PK)
    last_purchases = PurchaseHistory.objects.values("customer_ref").annotate(
        last_purchase=Max("purchased_at")
    )

    last_purchase_map = {
        entry["customer_ref"]: entry["last_purchase"]
        for entry in last_purchases
    }

    formatted = []
    for c in customers:
        full_address = (
            f"{c['soldtopartyaddress']}, "
            f"{c['soldtopartycity']}, "
            f"{c['soldtopartystate']} - {c['soldtopartypostal']}"
        )

        formatted.append({
            "id": c["id"],               # REAL PK
            "customerid": c["customerid"],
            "fullname": c["fullname"],
            "phone": c["primarycontact"],
            "address": full_address,
            "last_purchase": last_purchase_map.get(c["id"]),
        })

    return JsonResponse({"customers": formatted})


# ============================================================
# 1️⃣3️⃣ GET ONLY CUSTOMER PHONE (Optional)
# ============================================================
def customer_phone(request, cid):
    customer = customer_details.objects.filter(customerid=cid).first()
    if customer:
        return JsonResponse({"phone": customer.primarycontact})
    return JsonResponse({"phone": None})


def get_single_customer(request, id):
    try:
        c = customer_details.objects.get(customerid=id)
        return JsonResponse({
            "id": c.customerid,
            "fullname": c.fullname,
            "city": c.city or "",
            "state": c.state or "",
            "country": c.country or "",
            "pincode": c.pincode or "",
            "phone": str(c.primarycontact or c.secondarycontact or "")
        })
    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)


# ============================================================
# 1️⃣4️⃣ MESSAGE LOG VIEW
# ============================================================
def message_log_view(request):
    logs = SentMessageLog.objects.all().order_by('-created_at')[:100]
    return render(request, 'recommender/message_logs.html', {'logs': logs})

# ============================================================
# SEND MESSAGE API (Final RapBooster Version)
# ============================================================ 
import json, os, requests



# -----------------------------------------
# 🔧 Simple placeholder replace
# -----------------------------------------
def replace_placeholders(message, values: dict):
    if not message:
        return message
    for key, val in values.items():
        message = message.replace("{{" + key + "}}", str(val))
    return message


 
# ====================================================================
#   UNIFIED API — SEND WhatsApp / Email (Templates or Custom Message)
# ====================================================================

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from crmapp.models import customer_details, MessageTemplates
from recommender.rapbooster_api import (
    send_whatsapp_message,
    send_email_message,
    check_message_status
)

@csrf_exempt
def send_message_api(request):
    try:
        # ----------------- METHOD CHECK -----------------
        if request.method != "POST":
            return JsonResponse({"sent": False, "error": "POST only"}, status=405)

        # ----------------- PARSE PAYLOAD -----------------
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"sent": False, "error": "Invalid JSON"}, status=400)

        customer_id = payload.get("customer_id")
        template_id = payload.get("template_id")
        message_body = payload.get("message_body", "")
        send_channel = payload.get("send_channel", "whatsapp").lower()
        extra = payload.get("extra", {})
        poll_status = payload.get("poll_status", True)

        if not customer_id:
            return JsonResponse({"sent": False, "error": "Missing customer_id"}, status=400)

        # ----------------- FETCH CUSTOMER -----------------
        try:
            cust = customer_details.objects.get(id=customer_id)
        except customer_details.DoesNotExist:
            return JsonResponse({"sent": False, "error": "Customer not found"}, status=404)

        # ----------------- FETCH TEMPLATE -----------------
        template = None
        raw_body = message_body
        subject = "Notification"

        if template_id:
            template = MessageTemplates.objects.filter(id=template_id).first()
            if not template:
                return JsonResponse({"sent": False, "error": "Template not found"}, status=404)
            raw_body = template.body or ""
            if template.subject:
                subject = template.subject

        if not raw_body.strip():
            return JsonResponse({"sent": False, "error": "Message body empty"}, status=400)

        # ----------------- REPLACE PLACEHOLDERS -----------------
        final_body = replace_placeholders(
            raw_body,
            {
                "customer_name": cust.fullname,
                "phone": cust.primarycontact or "",
                "email": cust.primaryemail or "",
                **extra,
            },
        )

        # ----------------- VALIDATE CHANNEL -----------------
        if send_channel not in ["whatsapp", "email"]:
            return JsonResponse({"sent": False, "error": "Invalid send_channel"}, status=400)

        # ----------------- SEND MESSAGE -----------------
        log = None
        resp = None

        if send_channel == "whatsapp":
            if not cust.primarycontact:
                return JsonResponse({"sent": False, "error": "Customer has no phone"}, status=400)

            log, resp = send_whatsapp_message(
                phone=cust.primarycontact,
                message=final_body,
                customer_name=cust.fullname,
                customer=cust,
                template=template,
            )

        elif send_channel == "email":
            if not cust.primaryemail:
                return JsonResponse({"sent": False, "error": "Customer has no email"}, status=400)

            log, resp = send_email_message(
                email=cust.primaryemail,
                subject=subject,
                message=final_body,
                customer_name=cust.fullname,
                customer=cust,
                template=template,
            )

        if not log:
            return JsonResponse({"sent": False, "error": "Failed to create message log"}, status=500)

        # ----------------- DELIVERY STATUS -----------------
        status = log.status
        message_id = log.message_id
        delivery_status = log.delivery_status or status

        # Optional polling
        if poll_status and message_id:
            try:
                status_resp = check_message_status(message_id)
                delivery_status = status_resp.get("delivery_status", delivery_status)
                log.delivery_status = delivery_status
                log.save(update_fields=["delivery_status"])
            except Exception as ex:
                print(f"[Delivery Polling Error] {ex}")  # Log instead of silent pass

        # ----------------- RESPONSE -----------------
        return JsonResponse({
            "sent": status in ["queued", "sent", "delivered", "read"],
            "status": status,
            "message_id": message_id,
            "delivery_status": delivery_status,
            "provider": resp,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"sent": False, "error": str(e)}, status=500)


import threading
import time

def simulate_status_flow(log_id):
    def run():
        time.sleep(2)
        SentMessageLog.objects.filter(id=log_id).update(
            status="sent",
            delivery_status="sent"
        )

        time.sleep(3)
        SentMessageLog.objects.filter(id=log_id).update(
            status="delivered",
            delivery_status="delivered"
        )

        time.sleep(3)
        SentMessageLog.objects.filter(id=log_id).update(
            status="read",
            delivery_status="read"
        )

    threading.Thread(target=run).start()


#===================================================================
# SIMPLE API — WhatsApp Button (Customer Modal)
# ====================================================================

@csrf_exempt
def send_whatsapp(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    phone = request.POST.get("phone", "")
    message = request.POST.get("message", "")
    customer_id = request.POST.get("customer_id")

    customer = customer_details.objects.filter(id=customer_id).first()
    if not customer:
        return JsonResponse({"error": "Customer not found"}, status=404)

    status, provider = send_whatsapp_message(phone, message, customer)

    return JsonResponse({"status": status, "provider_response": provider})



# ====================================================================
# SIMPLE API — Email Button (Customer Modal)
# ====================================================================

@csrf_exempt
def send_email(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    email = request.POST.get("email", "")
    message = request.POST.get("message", "")
    subject = request.POST.get("subject", "Product Recommendation")
    customer_id = request.POST.get("customer_id")

    customer = customer_details.objects.filter(id=customer_id).first()
    if not customer:
        return JsonResponse({"error": "Customer not found"}, status=404)

    status, provider = send_email_message(email, subject, message)

    return JsonResponse({"status": status, "provider_response": provider})

from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator
@login_required

def message_logs(request):
    query = request.GET.get("q", "")
    channel = request.GET.get("channel", "")
    start_date = request.GET.get("start", "")
    end_date = request.GET.get("end", "")

    logs = SentMessageLog.objects.select_related("customer")

    # 🔍 Search (full text)
    if query:
        logs = logs.filter(
            Q(message__icontains=query) |
            Q(target__icontains=query) |
            Q(provider_response__icontains=query) |
            Q(customer__name__icontains=query)
        )

    # 🔔 Filter by channel
    if channel:
        logs = logs.filter(channel=channel)

    # 📅 Date filters
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)

    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)

    logs = logs.order_by("-timestamp")

    # 📄 Pagination (20 per page)
    paginator = Paginator(logs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "message_logs.html", {
        "page_obj": page_obj,
        "query": query,
        "channel": channel,
        "start_date": start_date,
        "end_date": end_date,
    })

def filter_logs(request):
    query = request.GET.get("q", "")
    channel = request.GET.get("channel", "")
    start_date = request.GET.get("start", "")
    end_date = request.GET.get("end", "")

    logs = SentMessageLog.objects.select_related("customer")

    if query:
        logs = logs.filter(
            Q(message__icontains=query) |
            Q(target__icontains=query) |
            Q(provider_response__icontains=query) |
            Q(customer__name__icontains=query)
        )

    if channel:
        logs = logs.filter(channel=channel)

    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)

    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)

    return logs.order_by("-timestamp")

def export_logs_csv(request):
    logs = filter_logs(request)

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="message_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(["Customer", "Channel", "Target", "Message", "API Response", "Timestamp"])

    for log in logs:
        writer.writerow([
            log.customer.name,
            log.channel,
            log.target,
            log.message,
            log.provider_response,
            log.timestamp,
        ])

    return response
def export_logs_excel(request):
    logs = filter_logs(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Message Logs"

    ws.append(["Customer", "Channel", "Target", "Message", "API Response", "Timestamp"])

    for log in logs:
        ws.append([
            log.customer.name,
            log.channel,
            log.target,
            log.message,
            log.provider_response,
            str(log.timestamp),
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = 'attachment; filename="message_logs.xlsx"'
    wb.save(response)

    return response

def export_logs_pdf(request):
    logs = filter_logs(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="message_logs.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()

    data = [
        ["Customer", "Channel", "Target", "Message", "API Response", "Timestamp"]
    ]

    for log in logs:
        data.append([
            log.customer.name,
            log.channel,
            log.target,
            log.message[:50],
            log.provider_response[:50],
            str(log.timestamp)
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))

    doc.build([table])
    return response





from crmapp.models import customer_details

def api_customers(request):
    customers = customer_details.objects.all()

    data = []
    for c in customers:
        primary = c.primarycontact if c.primarycontact else ""
        secondary = c.secondarycontact if c.secondarycontact else ""

        # Final fallback phone
        final_phone = ""
        if primary:
            final_phone = str(primary)
        elif secondary:
            final_phone = str(secondary)

        data.append({
            "customer_id": c.id,
            "customer_name": c.fullname,

            # Send all phone fields
            "primarycontact": str(primary),
            "secondarycontact": str(secondary),
            "phone": final_phone,     # REQUIRED
        })

    return JsonResponse({"customers": data})


@csrf_exempt
def rapbooster_webhook(request):
    # Allow browser GET testing
    if request.method == "GET":
        return JsonResponse({"message": "RapBooster Webhook Active", "method": "GET"})

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body.decode())

        message_id = data.get("message_id")
        status = data.get("status")

        if not message_id:
            return JsonResponse({"error": "message_id missing"}, status=400)

        log = SentMessageLog.objects.filter(message_id=message_id).first()

        if not log:
            return JsonResponse({"error": "No log found for message_id"}, status=404)

        status_mapping = {
            "sent": "sent",
            "delivered": "delivered",
            "read": "read",
            "failed": "failed",
            "queued": "queued"
        }

        log.status = status_mapping.get(status, "sent")
        log.provider_response = json.dumps(data)
        log.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

from crmapp.models import SentMessageLog, customer_details

def message_timeline_api(request, customer_id):
    logs = SentMessageLog.objects.filter(customer_id=customer_id).order_by("-created_at")

    data = []
    for log in logs:
        data.append({
            "id": log.id,
            "recipient": log.recipient,
            "channel": log.channel,
            "rendered_subject": log.rendered_subject,
            "rendered_body": log.rendered_body,
            "status": log.status,
            "message_id": log.message_id,
            "provider_response": log.provider_response,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": log.updated_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({"timeline": data})

# ---------------- PURCHASE HISTORY API ----------------

@require_GET 

# ----------- PURCHASE HISTORY API ----------- 

def get_purchase_history(request, customer_code):

    # Correct filtering using business customer code
    history = PurchaseHistory.objects.filter(
        customer__customerid=customer_code
    ).order_by("-purchased_at")

    data = []

    for row in history:
        # Product name logic
        product_name = (
            row.product.product_name if row.product else row.product_name
        )

        data.append({
            "product_name": product_name,
            "quantity": float(row.quantity),
            "total_amount": float(row.total_amount),
            "invoice_type": row.invoice_type,
            "purchased_at": row.purchased_at.strftime("%Y-%m-%d"),
        })

    return JsonResponse({"purchase_history": data})

# -------------------------------------------------------
# INTERNAL: Build unified purchase history list
# -------------------------------------------------------
def build_purchase_history(real_id, business_id):
    results = []

    # =====================================================
    # 1. NEW PurchaseHistory table (most reliable)
    # =====================================================
    ph_items = PurchaseHistory.objects.filter(customer_ref=real_id)
    for ph in ph_items:
        results.append({
            "product_id": getattr(ph.product, "product_id", None),
            "product_name": (
                ph.product.product_name if getattr(ph, "product", None)
                else ph.product_name
            ),
            "quantity": float(ph.quantity or 0),
            "total_amount": float(ph.total_amount or 0),
            "date": ph.purchased_at,
            "source": "purchase_history"
        })

    # =====================================================
    # 2. ServiceProduct → Product (FK)
    # =====================================================
    sp_items = ServiceProduct.objects.filter(service__custid_id=business_id)

    for s in sp_items:
        results.append({
            "product_id": s.product_id,
            "product_name": s.product.product_name,
            "quantity": None,
            "total_amount": None,
            "date": getattr(s.service, "date", None),
            "source": "service_product"
        })

    # =====================================================
    # 3. invoice → fuzzy match Product
    # =====================================================
    inv_items = invoice.objects.filter(custid_id=business_id)

    for inv in inv_items:
        rawname = (inv.description_of_goods or "").strip()
        if not rawname:
            continue

        # attempt to match product
        match = Product.objects.filter(
            Q(product_name__icontains=rawname)
        ).first()

        if match:
            results.append({
                "product_id": match.product_id,
                "product_name": match.product_name,
                "quantity": inv.quantity if hasattr(inv, "quantity") else None,
                "total_amount": inv.taxable_value if hasattr(inv, "taxable_value") else None,
                "date": inv.invoice_date,
                "source": "invoice"
            })

    # =====================================================
    # Sort final combined history by DATE descending
    # =====================================================
    results_sorted = sorted(
        results,
        key=lambda x: x["date"] or "",
        reverse=True
    )

    return results_sorted


# -------------------------------------------------------
# PUBLIC API: /api/purchase-history/<cid>/
# -------------------------------------------------------
@require_GET 

# -------------------------------------------------------------
# 2. Purchase History (Fix: customer_code instead of id) 


def api_purchase_history(request, customer_code):

    try:
        # Fetch customer using provided customer_code (customerid)
        customer = customer_details.objects.get(customerid=customer_code)

        # Fetch all purchase history linked via customer_int
        history = list(
            PurchaseHistory.objects.filter(
                customer_int=customer.id
            ).values(
                "id",
                "product_name",
                "quantity",
                "total_amount",
                "invoice_type",
                "purchased_at",
                "invoice_id",
                "tax_invoice_id",
                "product_id"
            ).order_by("-purchased_at")
        )

        return JsonResponse({
            "customer": {
                "id": customer.id,
                "customer_code": customer.customerid,
                "fullname": customer.fullname,
                "mobile": customer.primarycontact
            },
            "purchase_history": history
        })

    except customer_details.DoesNotExist:
        return JsonResponse({
            "error": "Customer not found",
            "purchase_history": []
        }, status=404)


# -------------------------------------------------------------
# 3. Demographic Recommendation
# -------------------------------------------------------------
def api_demographic_recommendation(request, customer_code):

    try:
        cust = customer_details.objects.get(customerid=customer_code)
    except customer_details.DoesNotExist:
        return JsonResponse({"recommendations": [], "error": "Customer not found"})

    # Filter similar customers
    similar_customers = customer_details.objects.filter(
        soldtopartycity=cust.soldtopartycity,
        soldtopartystate=cust.soldtopartystate,
        soldtopartypostal=cust.soldtopartypostal
    ).exclude(id=cust.id)

    # Aggregate popular items
    product_counts = (
        PurchaseHistory.objects.filter(customer_ref__in=similar_customers.values("id"))
        .values("product_name")
        .order_by()
    )

    product_list = [p["product_name"] for p in product_counts]

    return JsonResponse({
        "customer": cust.fullname,
        "city": cust.soldtopartycity,
        "state": cust.soldtopartystate,
        "region": cust.soldtopartypostal,
        "recommendations": product_list[:10]
    })




def api_personalized_recommendation(request, customer_code):
    """
    Returns AI personalized recommendations for a customer.
    Frontend uses BUSINESS customerid (string), 
    but recommendation model requires REAL PK (int).
    """

    # ----------------------------------------------------------------------
    # 1. Validate customer exists using business code
    # ----------------------------------------------------------------------
    try:
        cust = customer_details.objects.get(customerid=customer_code)
    except customer_details.DoesNotExist:
        return JsonResponse(
            {"error": "Customer not found", "recommendations": []},
            status=404
        )

    real_customer_id = cust.id  # PK needed for ML model

    # ----------------------------------------------------------------------
    # 2. Generate recommendations using hybrid model
    # ----------------------------------------------------------------------
    if hybrid_model is None:
        return JsonResponse({
            "error": "Hybrid model not loaded",
            "recommendations": []
        })

    try:
        raw_recommendations = hybrid_model.predict([real_customer_id])
    except Exception as e:
        return JsonResponse({
            "error": f"Model prediction failed: {e}",
            "recommendations": []
        })

    # ----------------------------------------------------------------------
    # 3. Normalize results (if model returns objects or strings)
    # ----------------------------------------------------------------------
    final_recs = []

    for item in raw_recommendations:
        try:
            # allow dict, object, or raw string
            if isinstance(item, dict):
                final_recs.append({
                    "product_id": item.get("product_id"),
                    "title": item.get("title") or item.get("product_name"),
                    "category": item.get("category"),
                    "tags": item.get("tags"),
                    "confidence_score": item.get("score"),
                })

            else:  
                # fallback: treat as raw product name
                final_recs.append({
                    "product_id": None,
                    "title": str(item),
                    "category": None,
                    "tags": None,
                    "confidence_score": None
                })

        except Exception:
            continue

    # ----------------------------------------------------------------------
    # 4. JSON Response
    # ----------------------------------------------------------------------
    return JsonResponse({
        "customer_id": real_customer_id,
        "customer_code": customer_code,
        "customer_name": cust.fullname,
        "recommendations": final_recs
    })



from django.http import JsonResponse
from django.db import connection
import pickle
import os

# ---------------------------------------------------------
# Load Model Once
# ---------------------------------------------------------
MODEL_FILE = os.path.join("recommender", "trained_models", "simple_cf_model.pkl")

try:
    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)
except Exception as e:
    model = None
    print("ERROR LOADING MODEL:", e)


# ---------------------------------------------------------
# Helper: Fetch user purchase history
# ---------------------------------------------------------
def get_user_history(customer_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT product_name 
            FROM crmapp_purchasehistory
            WHERE customer_id = %s
        """, [customer_id])
        rows = cursor.fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------
# Main Recommendation API
# --------------------------------------------------------- 


MODEL_PATH = "recommender/trained_models/simple_cf_model.pkl"

# ----------------------------------------------------
# Load model once (when server starts)
# ----------------------------------------------------
if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    pivot = model["pivot"]
    similarity = model["similarity"]
else:
    model = None
    pivot = None
    similarity = None

 

# --------------------------------------------------
# Load ML model once (on server start)
# --------------------------------------------------
MODEL_FILE = "recommender/trained_models/simple_cf_model.pkl"

try:
    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)
    pivot = model["pivot"]
    similarity = model["similarity"]

    MODEL_READY = True
    print("🔵 ML Model loaded in Django successfully.")

except Exception as e:
    MODEL_READY = False
    pivot = None
    similarity = None
    print("🔴 Failed to load ML model:", str(e))


# --------------------------------------------------
# Recommendation Function
# --------------------------------------------------
def generate_recommendations(customer_id, top_n=5):

    if pivot is None:
        return {
            "status": "ERROR",
            "message": "ML model not loaded"
        }

    if customer_id not in pivot.index:
        return {
            "status": "NO_DATA",
            "customer_id": customer_id,
            "products": []
        }

    # Find customer index
    cust_idx = pivot.index.tolist().index(customer_id)

    # Similarity row
    sim_scores = list(enumerate(similarity[cust_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Top similar users excluding self
    similar_users = [u for u, _ in sim_scores[1:6]]

    # Aggregate their purchases
    similar_products = pivot.iloc[similar_users].sum(axis=0)

    # Remove purchased items
    own = pivot.loc[customer_id]
    filtered = similar_products[own == 0]

    # Sort
    final = filtered.sort_values(ascending=False).head(top_n)

    return {
        "status": "OK",
        "customer_id": customer_id,
        "recommended_products": list(final.index),
        "scores": list(final.values)
    }


# --------------------------------------------------
# Django API Endpoint for Recommendation System
# --------------------------------------------------

#from .ml_service import get_recommendations



@csrf_exempt  

# --------------------------------------------
# Load trained CF model once at server startup
# -------------------------------------------- 
@login_required
@csrf_exempt
def get_recommendation_api(request, customer_id):
    """
    API: /api/get-recommendations/<customer_id>/
    """

    try:
        customer_id = int(customer_id)
    except ValueError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid customer_id format.",
            "recommendations": []
        }, status=400)

    result = get_recommendations(customer_id=customer_id, top_n=5)
    return JsonResponse(result, status=200, safe=False)

from django.http import JsonResponse
from .hybrid_service import get_hybrid_recommendations

def api_get_recommendations(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse({"error": "customer_id is required"}, status=400)

    recs = get_hybrid_recommendations(customer_id)

    if isinstance(recs, dict) and "error" in recs:
        return JsonResponse({"error": recs["error"]}, status=500)

    return JsonResponse({
        "customer_id": customer_id,
        "engine": "hybrid",
        "recommendations": recs
    })

# ============================================================
# 1) GET ML RECOMMENDATIONS
# ============================================================
@login_required
def api_get_ml_recommendations(request):
    try:
        customer_id = request.GET.get("customer_id")

        if not customer_id:
            return JsonResponse({"status": "error", "message": "Customer ID missing"}, status=400)

        recommendations = get_recommendations_for_customer(customer_id)

        return JsonResponse({
            "status": "success",
            "customer_id": customer_id,
            "recommendations": recommendations
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }, status=500)
 
# 2) GET CONTENT-BASED RECOMMENDATIONS (BY HISTORY)
# ============================================================
@login_required
def api_get_purchase_history(request):
    """
    Returns content-based product list from PurchaseHistory.
    """
    try:
        customer_id = request.GET.get("customer_id")

        if not customer_id:
            return JsonResponse({"status": "error", "message": "Customer ID missing"}, status=400)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT product_name, quantity, purchase_date
                FROM crmapp_purchasehistory
                WHERE customer_id = %s
                ORDER BY purchase_date DESC
                LIMIT 10
            """, [customer_id])

            rows = cursor.fetchall()

        history = [
            {
                "product_name": r[0],
                "quantity": float(r[1]) if r[1] else None,
                "purchase_date": str(r[2])
            } for r in rows
        ]

        return JsonResponse({
            "status": "success",
            "data": history
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
        

@require_GET
def fetch_saved_recommendations(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return HttpResponseBadRequest("customer_id is required")

    recs = PestRecommendation.objects.filter(customer_id=customer_id).order_by("-created_at")

    return JsonResponse({
        "customer_id": customer_id,
        "count": recs.count(),
        "data": list(recs.values())
    })


#1
# recommender/views.py

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

from .hybrid_service import get_hybrid_recommendations
from .recommender_engine import get_cf_recommendations
from .recommender_engine import get_content_based_recommendations


# ---------------------------------------------------------
# UTIL: Fetch Customer Info
# ---------------------------------------------------------
def fetch_customer_details(customer_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, fullname, primaryemail, primarycontact,
                   soldtopartyaddress, soldtopartycity, soldtopartystate,
                   soldtopartypostal
            FROM crmapp_customer_details
            WHERE customerid = %s
        """, [customer_id])
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "internal_id": row[0],
        "fullname": row[1],
        "email": row[2],
        "contact": row[3],
        "address": row[4],
        "city": row[5],
        "state": row[6],
        "postal": row[7],
    }


# ---------------------------------------------------------
# UTIL: Fetch Purchase History
# ---------------------------------------------------------
def fetch_purchase_history(customer_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT product_name, quantity, total_amount, purchased_at
            FROM crmapp_purchasehistory
            WHERE customer_id = %s
            ORDER BY purchased_at DESC
            LIMIT 50
        """, [customer_id])

        rows = cursor.fetchall()

    return [
        {
            "product_name": r[0],
            "quantity": float(r[1]),
            "total_amount": float(r[2]),
            "purchased_at": r[3].strftime("%Y-%m-%d %H:%M")
        }
        for r in rows
    ]


# ---------------------------------------------------------
# UPSALE / CROSS-SALE
# ---------------------------------------------------------
def generate_upsell_and_crosssell(base_product_id):
    """
    Upsell = higher-priced version of same category
    Cross-sell = frequently bought together
    """

    with connection.cursor() as cursor:

        # Upsell: same category, higher price
        cursor.execute("""
            SELECT id, product_name, selling_price
            FROM crmapp_productdetails
            WHERE category = (
                SELECT category FROM crmapp_productdetails WHERE id = %s
            )
            AND selling_price > (
                SELECT selling_price FROM crmapp_productdetails WHERE id = %s
            )
            ORDER BY selling_price ASC
            LIMIT 5
        """, [base_product_id, base_product_id])

        upsell_rows = cursor.fetchall()

        # Cross-sell
        cursor.execute("""
            SELECT p.id, p.product_name, p.selling_price
            FROM crmapp_productdetails p
            JOIN crmapp_purchasehistory ph
                ON p.id = ph.product_id
            WHERE ph.product_id != %s
            ORDER BY p.selling_price DESC
            LIMIT 5
        """, [base_product_id])

        crosssell_rows = cursor.fetchall()

    return {
        "upsell": [
            {"product_id": r[0], "name": r[1], "price": float(r[2])}
            for r in upsell_rows
        ],
        "crosssell": [
            {"product_id": r[0], "name": r[1], "price": float(r[2])}
            for r in crosssell_rows
        ]
    }


# ---------------------------------------------------------
# MAIN API: UNIFIED RECOMMENDATION ENGINE
# ---------------------------------------------------------
@require_GET
def unified_recommendation_api(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return HttpResponseBadRequest("customer_id required")

    # Fetch supporting data
    customer = fetch_customer_details(customer_id)
    purchase_history = fetch_purchase_history(customer_id)

    # Run 3 engines
    hybrid = get_hybrid_recommendations(customer_id, top_n=10)
    cf = get_cf_recommendations(customer_id, top_n=10)
    content = get_content_based_recommendations(customer_id, top_n=10)

    return JsonResponse({
        "customer": customer,
        "purchase_history": purchase_history,
        "recommendations": {
            "hybrid": hybrid,
            "collaborative_filtering": cf,
            "content_based": content
        }
    }, safe=False)


# ---------------------------------------------------------
# API: CF only
# ---------------------------------------------------------
@require_GET
def cf_api(request):
    customer_id = request.GET.get("customer_id")
    if not customer_id:
        return HttpResponseBadRequest("customer_id required")

    return JsonResponse(get_cf_recommendations(customer_id), safe=False)


# ---------------------------------------------------------
# API: Content-based only
# ---------------------------------------------------------
@require_GET
def content_api(request):
    customer_id = request.GET.get("customer_id")
    if not customer_id:
        return HttpResponseBadRequest("customer_id required")

    return JsonResponse(get_content_based_recommendations(customer_id), safe=False)


# ---------------------------------------------------------
# API: Hybrid only
# ---------------------------------------------------------
@require_GET
def hybrid_api(request):
    customer_id = request.GET.get("customer_id")
    if not customer_id:
        return HttpResponseBadRequest("customer_id required")

    return JsonResponse(get_hybrid_recommendations(customer_id), safe=False)


# ---------------------------------------------------------
# API: Upsell + Cross-sell (button click)
# ---------------------------------------------------------
@require_GET
def upsell_crosssell_api(request):
    product_id = request.GET.get("product_id")

    if not product_id:
        return HttpResponseBadRequest("product_id required")

    return JsonResponse(generate_upsell_and_crosssell(product_id), safe=False)



@csrf_exempt
def purchase_history(request, customer_id):
    try:
        with connection.cursor() as cursor:

            # Convert path parameter to int (customer_int)
            try:
                cid_int = int(customer_id)
            except:
                cid_int = None

            query = """
                SELECT 
                    id,
                    product_name,
                    quantity,
                    total_amount,
                    invoice_type,
                    purchased_at,
                    customer_id,
                    customer_int,
                    invoice_id
                FROM crmapp_purchasehistory
                WHERE customer_int = %s
                ORDER BY purchased_at DESC
                LIMIT 100;
            """

            cursor.execute(query, [cid_int])
            rows = cursor.fetchall()

        # No history found
        if not rows:
            return JsonResponse({
                "status": True,
                "customer_id": customer_id,
                "history": []
            })

        # Format result
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "product_name": row[1],
                "quantity": float(row[2]),
                "total_amount": float(row[3]),
                "invoice_type": row[4],
                "purchased_at": row[5].strftime("%Y-%m-%d %H:%M"),
                "customer_code": row[6],     # SANKAP4923, etc.
                "customer_int": row[7],
                "invoice_id": row[8]
            })

        return JsonResponse({
            "status": True,
            "customer_id": customer_id,
            "history": history
        })

    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)


from django.views.decorators.http import require_GET 
from django.views.decorators.http import require_GET
from django.http import JsonResponse

from crmapp.models import Product, customer_details
 

from rest_framework.decorators import api_view
from rest_framework.response import Response
from crmapp.models import PurchaseHistory, customer_details
from .serializers import PurchaseHistorySerializer
from .purchase_history_serializer import PurchaseHistorySerializer

@api_view(["GET"])
def get_purchase_history(request, customer_code):
    try:
        customer = customer_details.objects.get(customerid=customer_code)
    except customer_details.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    history = PurchaseHistory.objects.filter(customer=customer).order_by("-purchased_at")

    serializer = PurchaseHistorySerializer(history, many=True)

    return Response({
        "customer": customer.fullname,
        "customer_id": customer.customerid,
        "purchase_history_count": len(serializer.data),
        "purchase_history": serializer.data
    })


from datetime import datetime

 
from datetime import date, timedelta

from datetime import date
from django.http import JsonResponse
from crmapp.models import CustomerContract, customer_details,service_management


# -------------------------------------------------------
# 📌 FETCH CONTRACT (WORKS WITH STRING customer_id) 

def get_customer_contract(request, customer_id):

    try:
        # customer_id from frontend is customer.customerid (string)
        customer = customer_details.objects.get(customerid=customer_id)

        # latest service record (contract)
        service = service_management.objects.filter(
            customer_id=customer.id
        ).latest("service_date")

        return JsonResponse({
            "exists": True,
            "contract_type": service.contract_type,
            "start_date": service.service_date,
            "lead_date": service.lead_date,
            "status": service.contract_status,
            "service_id": service.id,
        })

    except service_management.DoesNotExist:
        return JsonResponse({"exists": False})

    except customer_details.DoesNotExist:
        return JsonResponse({"exists": False})


@csrf_exempt
def save_customer_contract(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        data = json.loads(request.body)

        # Frontend sends customerid (string code) → find real PK
        customer_code = data.get("customer_id")
        contract_type = data.get("contract_type")
        start_date = data.get("start_date")

        if not (customer_code and contract_type and start_date):
            return JsonResponse({"success": False, "error": "Missing fields"})

        # Get REAL customer object
        customer = customer_details.objects.get(customerid=customer_code)

        # -------------------------
        # 1️⃣ Save in service management (REAL CONTRACT TABLE)
        # -------------------------
        service = service_management.objects.create(
            customer_id=customer.id,
            contract_type=contract_type,
            contract_status="Active",
            state=customer.soldtopartystate,
            city=customer.soldtopartycity,
            pincode=customer.soldtopartypostal,
            address=customer.soldtopartyaddress,
            payment_terms="Standard",
            frequency_count="1",
            lead_date=date.today(),
            service_date=start_date,
            gst_status="Yes",
            service_subject=f"{contract_type} Contract"
        )

        # -------------------------
        # 2️⃣ SAVE DEFAULT LINE-ITEM IN SERVICEPRODUCT
        # -------------------------
        # Fetch any product belonging to this contract type (optional logic)
        default_product = Product.objects.filter(
            product_name__icontains=contract_type.split()[0]
        ).first()

        if default_product:
            ServiceProduct.objects.create(
                service_id=service.id,
                product_id=default_product.product_id,
                price=0,
                quantity=1,
                gst_percentage=0,
                total_with_gst=0,
                description=f"{contract_type} Base Contract"
            )

        return JsonResponse({
            "success": True,
            "message": "Contract saved successfully",
            "service_id": service.id
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


from django.http import JsonResponse
from .demographic_service import (
    get_demographic_recommendations,
    save_demographic_recommendations
)
from .models import PestRecommendation


def generate_demographic_recommendations(request, customer_id):
    try:
        customer_pk = int(customer_id)
        customer_details.objects.get(id=customer_pk)  # validate FK
    except:
        return JsonResponse({"status": "error", "message": "Invalid customer ID"})

    result = get_demographic_recommendations(customer_pk)

    if result["status"] != "success":
        return JsonResponse(result)

    # Delete old demographic rows
    PestRecommendation.objects.filter(
        customer_id=customer_pk,
        recommendation_type="demographic"
    ).delete()

    formatted = [
        {"product_id": pid, "score": 1.0}
        for pid in result["recommended_products"]
    ]

    save_demographic_recommendations(customer_pk, formatted)

    return JsonResponse({
        "status": "success",
        "city": result["city"],
        "state": result["state"],
        "postal_code": result["postal_code"],
        "total_products": result["total_products"]
    })

from django.http import JsonResponse
from .recommender_engine import generate_full_recommendations


def generate_recommendations(request, customer_id):
    """
    Universal API — Hybrid + Demographic
    """
    result = generate_full_recommendations(customer_id, top_n=10)
    return JsonResponse(result, safe=False)


from django.http import JsonResponse
from .demographic_service import get_demographic_recommendations, save_demographic_recommendations

def demographic_recommend_api(request, customer_id):
    result = get_demographic_recommendations(customer_id)

    if result["status"] != "success":
        return JsonResponse(result, status=404)

    # Save to DB
    save_demographic_recommendations(
        customer_id,
        [{"product_id": item["product_id"], "score": item["score"]}
         for item in result["recommended_products"]]
    )

    return JsonResponse(result, safe=False)



from django.http import JsonResponse
from crmapp.models import service_management


def service_purchase_history(request, customer_id):
    services = (
        service_management.objects
        .filter(customer_id=customer_id)
        .order_by('-service_date', '-lead_date')
    )

    result = []

    for s in services:
        result.append({
            "service_name": s.service_subject or "Service",
            "contract_type": s.contract_type,
            "status": s.contract_status,
            "amount": float(s.total_price_with_gst or 0),
            "start_date": (
                s.service_date.isoformat()
                if s.service_date else
                s.lead_date.isoformat()
            )
        })

    return JsonResponse({"services": result})


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from recommender.hybrid_recommender import get_hybrid_recommendations


@api_view(["GET"])
def hybrid_recommendations_api(request, customer_id):
    """
    API: Get hybrid recommendations for a customer
    Includes:
    - Service upsell
    - CF / fallback product recommendations
    """

    try:
        recommendations = get_hybrid_recommendations(customer_id=customer_id)

        return Response(
            {
                "customer_id": customer_id,
                "total_recommendations": len(recommendations),
                "recommendations": recommendations,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


from django.http import JsonResponse
from recommender.models import PestRecommendation

def served_recommendations(request, customer_id):
    recos = (
        PestRecommendation.objects
        .filter(customer_id=customer_id, serving_state='served')
        .order_by('-final_rank_score')
    )

    data = []
    for r in recos:
        data.append({
            "item_id": r.recommended_item_id,
            "channel": r.reco_channel,
            "recommendation_type": r.recommendation_type,
            "score": float(r.final_rank_score),
            "explanation": r.explanation
        })

    return JsonResponse({
        "customer_id": customer_id,
        "recommendations": data
    })


from django.http import JsonResponse
from recommender.models import PestRecommendation

def served_product_recommendations(request, customer_id):
    recos = (
        PestRecommendation.objects
        .filter(
            customer_id=customer_id,
            serving_state='served',
            reco_channel='product'
        )
        .order_by('-final_rank_score')
    )

    data = [{
        "product_id": r.recommended_product_id,
        "recommendation_type": r.recommendation_type,
        "score": float(r.final_rank_score),
        "explanation": r.explanation
    } for r in recos]

    return JsonResponse({
        "customer_id": customer_id,
        "type": "product",
        "recommendations": data
    })

def served_service_recommendations(request, customer_id):
    recos = (
        PestRecommendation.objects
        .filter(
            customer_id=customer_id,
            serving_state='served',
            reco_channel='service'
        )
        .order_by('-final_rank_score')
    )

    data = [{
        "service_id": r.recommended_service_id,
        "recommendation_type": r.recommendation_type,
        "score": float(r.final_rank_score),
        "explanation": r.explanation
    } for r in recos]

    return JsonResponse({
        "customer_id": customer_id,
        "type": "service",
        "recommendations": data
    })



from django.shortcuts import render
from django.utils import timezone 
from django.http import JsonResponse
from django.utils import timezone
import uuid

from recommender.models import (
    PestRecommendation,
    RecommendationInteraction
)


from django.utils import timezone
import uuid

def customer_recommendations(request, customer_id):
    recos = PestRecommendation.objects.filter(customer_fk=customer_id)

    now = timezone.now()

    for r in recos:
        if r.exposed_at:
            continue

        exposure_id = str(uuid.uuid4())

        r.exposed_at = now
        r.exposure_channel = 'crm'
        r.exposure_id = exposure_id
        r.serving_state = 'exposed'
        r.save(update_fields=[
            'exposed_at',
            'exposure_channel',
            'exposure_id',
            'serving_state'
        ])

        RecommendationInteraction.objects.create(
            recommendation=r,
            customer=r.customer,
            product=r.recommended_product,
            interaction_type='exposed',
            interaction_channel='crm',
            event_time=now,
            exposure_id=exposure_id,
            metadata={"source": "crm_ui"}
        )

    return JsonResponse({"count": recos.count()})

from recommender.message_builder import build_recommendation_message

def get_customer_message(request, customer_id):
    customer = customer_details.objects.get(customerid=customer_id)

    recommendations = PestRecommendation.objects.filter(
        customer_fk=customer.id,
        serving_state="pending",
        is_active=1
    ).order_by("priority", "-final_score")

    message = build_recommendation_message(customer, recommendations)

    return JsonResponse({"message": message})




from django.http import JsonResponse
from crmapp.models import customer_details
from recommender.models import PestRecommendation
from recommender.services.message_builder import MessageBuilder
from recommender.services.recommendation_fetcher import (
    fetch_upsell,
    fetch_crosssell,
)


def customer_message_api(request, customer_code):

    # 1️⃣ Resolve customer (STRING → DB)
    try:
        customer = customer_details.objects.get(customerid=customer_code)
    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    # 2️⃣ Single source of truth (NO ORM LEAKS)
    recommendations = {
        "upsell": fetch_upsell(customer),
        "cross_sell": fetch_crosssell(customer),
    }

    # 3️⃣ Channel-aware message
    channel = request.GET.get("channel", "whatsapp")

    message_body = MessageBuilder.build(
        customer=customer,
        recommendations=recommendations,
        channel=channel,
    )

    return JsonResponse({
        "status": "success",
        "customer_code": customer.customerid,
        "customer_name": customer.fullname,
        "primary_contact": customer.primarycontact,
        "primary_email": customer.primaryemail,

        # 🔑 UI & Analytics Ready
        "recommendations": recommendations,

        # 🔑 Messaging Ready
        "message_body": message_body,
    })


from django.http import JsonResponse
from crmapp.models import customer_details
from recommender.services.recommendation_fetcher import (
    fetch_upsell,
    fetch_crosssell,
)
from recommender.services.message_builder import MessageBuilder


# -------------------------------
# RECOMMENDATIONS VIEW
# -------------------------------


from recommender.messaging.composer import compose_message
def recommendations_view_part(request, customer_code):
    customer = get_object_or_404(
        customer_details,
        customerid=customer_code
    )


    channel = request.GET.get("channel", "whatsapp")


    recommendations = {
        "upsell": fetch_upsell(customer),
        "cross_sell": fetch_crosssell(customer),
    }


    message_body = compose_message(
        customer=customer,
        recommendations=recommendations,
        channel=channel
    )


    return JsonResponse({
        "status": "success",
        "customer_code": customer.customerid,
        "recommendations": recommendations,
        "message_body": message_body
    })



def recommendation_message_view(request, customer_code):
    customer = get_object_or_404(
        customer_details,
        customerid=customer_code
    )


    recommendations = {
        "upsell": fetch_upsell(customer),
        "cross_sell": fetch_crosssell(customer),
    }


    template = MessageTemplates.objects.get(
        is_default=True
    ).body


    message_body = compose_message(
        template,
        customer,
        recommendations
    )


    return JsonResponse({
        "customer": customer.customerid,
        "message_body": message_body,
        "recommendations": recommendations
 })

# -------------------------------
# CUSTOMER MESSAGE VIEW
# -------------------------------
def customer_message_view(request, customer_code):
    channel = request.GET.get("channel", "whatsapp")

    try:
        customer = customer_details.objects.get(customerid=customer_code)
    except customer_details.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    recommendations = {
        "upsell": fetch_upsell(customer),
        "cross_sell": fetch_crosssell(customer),
    }

    message = MessageBuilder.build(
        customer=customer,
        recommendations=recommendations,
        channel=channel,
    )

    return JsonResponse({
        "customer_code": customer.customerid,
        "message": message,
    })


@csrf_exempt
def customer_reply_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body)

        recommendation_id = payload.get("recommendation_id")
        action = payload.get("action")  # accepted / rejected

        if action not in ["accepted", "rejected"]:
            return JsonResponse({"error": "Invalid action"}, status=400)

        rec = PestRecommendation.objects.get(id=recommendation_id)

        rec.action = action
        rec.responded_at = timezone.now()
        rec.save(update_fields=["action", "responded_at"])

        return JsonResponse({
            "status": "success",
            "recommendation_id": rec.id,
            "action": action
        })

    except PestRecommendation.DoesNotExist:
        return JsonResponse({"error": "Recommendation not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

 
from recommender.pipelines.service_regenerator import regenerate_services

from django.db.models import Max, Q
from django.utils import timezone

from django.db.models import Max, Q
from django.utils import timezone

from recommender.models import PestRecommendation
from crmapp.models import service_management


from django.db.models import Max, Q
from django.utils import timezone
from recommender.models import PestRecommendation
from crmapp.models import service_management

VALID_SERVICE_SUBJECTS = {
    "General Pest Control",
    "Cockroach Management Service",
    "Bed Bugs Management",
    "Bed Bug Management Service",
    "Rodent Control Service",
}


def get_recommendations(customer_id, intent, limit_products=7, limit_services=3):

    now = timezone.now()

    base_filter = Q(
        business_intent=intent,
        is_active=1
    ) & (
        Q(valid_until__isnull=True) |
        Q(valid_until__gt=now)
    )

    # ---------------- CUSTOMER SCOPE ----------------
    if customer_id not in (None, "ALL"):
        customer_filter = Q(canonical_customer_id=customer_id)
    else:
        customer_filter = Q()

    qs = PestRecommendation.objects.filter(base_filter & customer_filter)

    # ---------------- PRODUCTS ----------------
    products = list(
        qs.filter(
            reco_channel="product",
            recommended_product_id__isnull=False
        )
        .values(
            product_id=Max("recommended_product_id"),
            product_name=Max("recommended_product__product_name"),
            confidence=Max("final_score")
        )
        .order_by("-confidence")[:limit_products]
    )

    # ---------------- SERVICES ----------------
    services = []

    if customer_id not in (None, "ALL"):
        service_qs = (
            service_management.objects
            .filter(
                customer_id=customer_id,
                contract_status="Completed",
                service_subject__in=VALID_SERVICE_SUBJECTS
            )
            .values("service_subject")
            .annotate(confidence=Max("total_price"))
            .order_by("-confidence")[:limit_services]
        )

        services = [
            {
                "service_id": idx + 1,  # UI-safe synthetic id
                "service_name": s["service_subject"],
                "confidence": 0.85
            }
            for idx, s in enumerate(service_qs)
        ]

    # ---------------- GLOBAL FALLBACK ----------------
    if customer_id not in (None, "ALL") and not products and not services:
        return get_recommendations(
            customer_id="ALL",
            intent=intent,
            limit_products=limit_products,
            limit_services=limit_services
        )

    return products, services


from django.http import JsonResponse 
from recommender.pipelines.service_regenerator import regenerate_services

def regenerate_service_view(request, customer_id):
    intent = request.GET.get("intent", "upsell")

    count = regenerate_services(customer_id, intent)

    return JsonResponse({
        "status": "success",
        "intent": intent,
        "services_created": count
    })




from django.http import JsonResponse
from crmapp.models import customer_details
from recommender.message_composer import compose_prompt
from open_ai.views import generate_ai_message
from recommender.queries import fetch_recommendations

def generate_message(request, customer_id):
    channel = request.GET.get("channel", "whatsapp")

    customer = customer_details.objects.get(id=customer_id)
    recommendations = fetch_recommendations(customer.id)

    if not recommendations:
        return JsonResponse({
            "status": "empty",
            "message": "No recommendations available"
        })

    prompt = compose_prompt(
        customer_name=customer.customer_name,
        channel=channel,
        recommendations=recommendations
    )

    message = generate_ai_message(prompt)

    return JsonResponse({
        "status": "success",
        "customer": customer.customer_name,
        "channel": channel,
        "message": message
    })


from crmapp.models import MessageTemplates

def get_message_template(channel, category, lead_status=None):
    qs = MessageTemplates.objects.filter(
        message_type=channel,
        category=category,
        is_active=True
    )

    if lead_status:
        qs = qs.filter(lead_status=lead_status)

    return qs.first()


from django.http import JsonResponse
from crmapp.models import customer_details 
from .views import get_message_template

from django.http import JsonResponse
from crmapp.models import SentMessageLog
from recommender.rapbooster_status import fetch_message_status


def message_status_api(request, message_id):

    try:
        log = SentMessageLog.objects.get(message_id=message_id)
    except SentMessageLog.DoesNotExist:
        return JsonResponse({"error": "Message not found"}, status=404)

    provider_status = fetch_message_status(message_id)

    new_status = provider_status.get("status", "").lower()

    if new_status and new_status != log.status:
        log.status = new_status
        log.provider_response = str(provider_status)
        log.save(update_fields=["status", "provider_response"])

    return JsonResponse({
        "message_id": message_id,
        "channel": log.channel,
        "status": log.status.upper()
    })


from crmapp.models import SentMessageLog
 

def populate_message_with_recommendations(customer_id, template_body):
    """
    Returns message body populated with recommended products/services
    """

    # Fetch recommended products/services for this customer
    recs = PestRecommendation.objects.filter(
        customer_id=customer_id,
        is_active=True
    )

    products = [r.product_name for r in recs if r.recommendation_type == 'product']
    services = [r.service_name for r in recs if r.recommendation_type == 'service']

    # Inject into message template
    message_body = template_body
    if products:
        message_body += "\n\nRecommended Products:\n- " + "\n- ".join(products)
    if services:
        message_body += "\n\nRecommended Services:\n- " + "\n- ".join(services)

    return message_body, products, services


from .rapbooster_api import send_to_rapbooster
 

def send_message(customer, template_body, channel='whatsapp'):
    """
    Sends a message to a customer, auto-populating recommended products/services.
    """

    # 🔹 Fetch active recommendations
    recs = PestRecommendation.objects.filter(
        customer_fk=customer.id,
        is_active=True
    )

    products = [r.product_name for r in recs if r.recommendation_type == 'product']
    services = [r.service_name for r in recs if r.recommendation_type == 'service']

    # 🔹 Inject recommendations into message body
    message_body = template_body
    if products:
        message_body += "\n\nRecommended Products:\n- " + "\n- ".join(products)
    if services:
        message_body += "\n\nRecommended Services:\n- " + "\n- ".join(services)

    # 🔹 Create initial DB log (queued)
    msg_log = SentMessageLog.objects.create(
        customer=customer,
        message_body=message_body,
        recommended_products=products,
        recommended_services=services,
        channel=channel,
        status='queued'
    )

    # 🔹 Send via RapBooster API (mock or real)
    send_to_rapbooster(msg_log)

    return msg_log
