# recommender/urls.py

from django.urls import path
from . import views
from .api import recommend_products
from . import api_recommend
from .views_purchase_history import get_purchase_history
from .views_pest_recommendations import get_pest_recommendations
from recommender.api_recommend import recommendation_api
from .views import recommendation_ui, recommendations_view



from recommender.views import hybrid_recommendations_api,served_recommendations,served_product_recommendations,served_service_recommendations ,customer_recommendations,customer_message_api,customer_reply_api,regenerate_service_view, generate_message
from recommender.api_feedback import recommendation_feedback
from .rapbooster_webhooks import rapbooster_delivery_callback
from .api_views import api_message_status
from .api_views import rapbooster_webhook 
from .views_webhook import rapbooster_delivery_webhook


from .api_views import send_message_api, message_status_api
# API Views
from .views import (
    api_ai_personalized,
    message_timeline_api,
    api_purchase_history,
    get_recommendation_api,
    message_logs,
    api_purchase_history,
    
)
from .views import get_purchase_history,get_all_customers, upsell_view, crosssell_view,service_purchase_history
from recommender.api_demographic import demographic_recommendations

# External API modules
from .api_views import api_send_message, api_customer_details, api_get_customers
from .recommend_api import get_recommendations
from .api_recommend import final_recommend_api
from .views import purchase_history



urlpatterns = [

    # ======================================
    # 🌐 MAIN UI PAGES
    # ======================================
    path('ui/', views.recommendation_ui, name='recommendation_ui'),
  
    path('dashboard/', views.recommendation_dashboard, name='recommendation_dashboard'),
    path('message-logs/', views.message_log_view, name='message_log_view'),

    # ======================================
    # 🧠 CORE PRODUCT & CUSTOMER API
    # ======================================
    path('api/products/', views.get_all_products, name='get_all_products'),
    path('api/customers/', views.get_all_customers, name='get_all_customers'),
    path('api/customer/<int:cid>/phone/', views.customer_phone, name='customer_phone'),

    # ======================================
    # 🧠 AI & RECOMMENDATION ENDPOINTS
    # ======================================
    path('api/recommendations/', views.recommendations_view, name='api_recommendations'),
    path('api/recommendations/<int:customer_id>/', api_ai_personalized, name='api_recommendations_customer'),
    path('api/user_recommendations/<int:customer_id>/', api_ai_personalized, name='api_user_recommendations'),
    path('api/customer_recommendations/<int:customer_id>/', views.customer_recommendations_api, name='customer_recommendations_api'),

    # Collaborative / Upsell / Cross-sell
    path('api/collaborative/<int:customer_id>/', views.collaborative_view, name='api_collaborative'),
    #path('api/upsell/<int:product_id>/', views.upsell_view, name='api_upsell'),
   # path('api/crosssell/<int:customer_id>/', views.crosssell_view, name='api_crosssell'),
   # path('api/upsell/<int:customer_id>/', views.upsell_view, name='api_upsell'),
    #path("api/upsell/<int:customer_id>/", views.upsell_view),
   #path('api/upsell/<int:customer_id>/<int:product_id>/', views.upsell_view, name='api_upsell'),
    
     #path('api/popular-products/<str:customer_id>/', views.popular_products_api),

      # Cross-sell
    path('api/crosssell/<int:customer_id>/', views.crosssell_view, name='api_crosssell'),

    # Upsell (customer + product)
    path('api/upsell/<int:customer_id>/<int:product_id>/', views.upsell_view, name='api_upsell'),

    # Popular products
    #path('api/popular-products/<str:customer_id>/', views.popular_products_api, name='api_popular_products'),
#path("api/recommendations/upsell/<str:customer_id>/", views.upsell_view),
#path("api/recommendations/crosssell/<str:customer_id>/", views.crosssell_view),

    path(
        "api/recommendations/upsell/<str:customer_id>/",
        upsell_view,
        name="upsell"
    ),
    path(
        "api/recommendations/crosssell/<str:customer_id>/",
        crosssell_view,
        name="crosssell"
    ),


    # ======================================
    # 💬 MESSAGE GENERATION & SENDING
    # ======================================
    path('api/generate-message/', views.generate_message, name='api_generate_message'),

    # ONLY ONE FINAL send-message endpoint
    #path('api/send-message/', api_send_message, name='api_send_message'), 
    path(
    'api/send-message/',
    send_message_api,
    name='send_message_api'
),




    # ======================================
    # 📂 Customer Details
    # ======================================
   # path('customers/', api_get_customers, name='api_get_customers'),
   
    path("customers/", get_all_customers, name="get_all_customers"),
    path('customer/<int:cid>/details/', api_customer_details, name='api_customer_details'),

    # ======================================
    # 📩 Direct WhatsApp & Email
    # ======================================
    path('send_whatsapp/', views.send_whatsapp, name='send_whatsapp'),
    path('send_email/', views.send_email, name='send_email'),

    # ======================================
    # 📜 Logs & Export
    # ======================================
    path('logs/', message_logs, name='message_logs'),
    path('logs/messages/', message_logs, name='message_logs'),
    path('message-logs/export/csv/', views.export_logs_csv, name='export_logs_csv'),
    path('message-logs/export/excel/', views.export_logs_excel, name='export_logs_excel'),
    path('message-logs/export/pdf/', views.export_logs_pdf, name='export_logs_pdf'),

    # ======================================
    # 🔄 Timeline
    # ======================================
    path("timeline/<int:customer_id>/", message_timeline_api, name="timeline_api"),

    # ======================================
    # 🛒 Purchase History
    # ======================================
    path("recommendations/api/purchase-history/<int:cid>/", api_purchase_history),

    # ======================================
    # ⭐ Final Working Recommendation Endpoints
    # ======================================
    path("api/recommend/<str:customer_id>/", get_recommendations, name="api_recommend"),
    path("get_recommendations/<int:customer_id>/", get_recommendation_api, name="get_recommendation_api"),
    # ⭐ Final Unified Recommendation API
path("api/final/recommend/<int:customer_id>/", final_recommend_api, name="final_recommend_api"),

path("recommend/", recommend_products, name="recommend-products"),
 path("api/recommend/<str:customer_id>/", api_recommend.final_recommend_api, name="final_recommend_api"),


 path("api/recommend/", views.unified_recommendation_api, name="unified_recommend"),
    path("api/cf/", views.cf_api, name="cf"),
    path("api/content/", views.content_api, name="content"),
    path("api/hybrid/", views.hybrid_api, name="hybrid"),
    path("api/upsell/", views.upsell_crosssell_api, name="upsell_crosssell"),

  #  path("api/customers/<int:id>/", views.get_single_customer, name="get_single_customer"),
  #  path("api/purchase-history/<int:cid>/", api_purchase_history),
    path("api/recommend/", views.unified_recommendation_api),

    path("recommendations/api/purchase-history/<int:cid>/", api_purchase_history),
    path("api/recommendations/<int:cid>/", api_ai_personalized),

    path("recommend-products/", recommend_products, name="recommend_products"),

 

    path("api/customers/", views.get_all_customers),
    path("api/recommendations/<str:cust_id>/", views.get_recommendations),
   
    path("api/recommendations/<str:customer_id>/", get_recommendations),
   
     
      path("api/demographic/<int:customer_id>/", demographic_recommendations),
      path("demographic/<int:customer_id>/", demographic_recommendations),
     
       path("api/demographic/<int:customer_id>/", demographic_recommendations, name="demographic_recommendations"),
      
      # path("purchase-history/<int:customer_id>/", get_purchase_history),
       path("pest-recommendations/<int:customer_id>/", get_pest_recommendations),
       path("api/recommend/demographic/<int:customer_id>/", demographic_recommendations),
       path("demographic-recommendations/<int:customer_id>/", demographic_recommendations),

       
    path("customers/", get_all_customers, name="get_all_customers"),
    #path("api/purchase-history/<str:customer_code>/", api_purchase_history)
   # path("api/purchase-history/<customerid>/", api_purchase_history, name="api_purchase_history"),

    path("api/purchase-history/<str:customer_code>/", api_purchase_history),


    path("save-contract/", views.save_customer_contract, name="save_contract"),
    path("get-contract/<str:customer_id>/", views.get_customer_contract, name="get_contract"),
    
    path("demographic/<int:customer_id>/", views.generate_demographic_recommendations, name="demographic_recommend"),
    path("recommend/<int:customer_id>/", views.generate_recommendations, name="recommend"),
    path("api/recommend/demographic/<int:customer_id>/", 
     views.demographic_recommend_api, 
     name="demographic_recommend"),

     path(
    "api/service-history/<int:customer_id>/",
    service_purchase_history
),

    path("api/recommendations/", recommendation_api, name="recommendations"),
       path(
        "hybrid/<int:customer_id>/",
        hybrid_recommendations_api,
        name="hybrid-recommendations",
    ), 
       path(
        'api/recommendations/<str:customer_id>/',
        served_recommendations,
        name='served_recommendations'
    ),

    # ✅ Debug / internal (optional)
    path(
        'api/recommendations/all/<str:customer_id>/',
        get_recommendations,
        name='get_recommendations'
    ),
    path('api/recommendations/<str:customer_id>/', served_recommendations),
    path('api/recommendations/products/<str:customer_id>/', served_product_recommendations),
    path('api/recommendations/services/<str:customer_id>/', served_service_recommendations),
    path("recommendations/feedback/", recommendation_feedback),

     path(
        'api/recommendations/<int:customer_id>/',
        customer_recommendations,
        name='customer_recommendations'
    ),

 
    path(
        "customer-message/<str:customer_code>/",
        customer_message_api,
        name="customer_message_api"
    ),

   

    path(
        "customer-message/<str:customer_code>/",
        views.customer_message_view,
        name="customer_message"
    ),

     path("api/customer-reply/", customer_reply_api),

        path(
        "recommendations/views/<str:customer_code>/",
        views.recommendations_view_part,
        name="recommendations"
    ),

    path(
    "api/recommendations/regenerate/services/<int:customer_id>/",
    regenerate_service_view
),
path("generate-message/<int:customer_id>/", generate_message),
 path("api/rapbooster/callback/", rapbooster_delivery_callback),
 
    path("api/message-status/<str:message_id>/", api_message_status),
    
    path("api/rapbooster/webhook/", rapbooster_webhook),


    
    path("send-message/", send_message_api),
    path("message-status/<str:message_id>/", message_status_api),

    path("api/message-status/<str:message_id>/", message_status_api),
    
   # path("api/rapbooster/webhook/", rapbooster_delivery_webhook),
     path(
        "webhooks/rapbooster/delivery/",
        rapbooster_delivery_webhook,
        name="rapbooster_delivery_webhook"
    ), 










]

