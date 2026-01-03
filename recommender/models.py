from django.db import models
from crmapp.models import Product, customer_details, MessageTemplates,service_management

# ---------------------------------------------------
# ITEM TABLE → connected to Product
# ---------------------------------------------------
class Item(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=128)
    tags = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        db_column='product_id',
        related_name='item',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'recommender_item'

    def __str__(self):
        return self.title


# ---------------------------------------------------
# RATING TABLE (customer + product)
# ---------------------------------------------------
class Rating(models.Model):
    id = models.BigAutoField(primary_key=True)
    rating = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column='product_id',
        related_name='rating_products',   # FIXED
        null=True,
        blank=True
    )

    customer = models.ForeignKey(
        customer_details,
        on_delete=models.CASCADE,
        db_column='customer_id',
        related_name='rating_customers',  # FIXED
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'recommender_rating'

    def __str__(self):
        return f"{self.customer.fullname if self.customer else 'Unknown'} → {self.product.product_name if self.product else 'Unknown'}: {self.rating}"


# =========================================================
# Saved ML models
# =========================================================
class SavedModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    file_path = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =========================================================
# INTERACTIONS LOG
# ========================================================= 
class Interaction(models.Model):
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('click', 'Click'),
        ('purchase', 'Purchase'),
        ('call', 'Call'),
        ('recommend', 'Recommendation Shown'),
    ]

    customer = models.ForeignKey(
        customer_details,
        on_delete=models.CASCADE,
        related_name='interaction_customers',
        null=True,      # ADD THIS
        blank=True      # ADD THIS
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='interaction_products',
        null=True,      # ADD THIS
        blank=True      # ADD THIS
    )

    interaction_type = models.CharField(max_length=50, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'recommender_interaction'
        unique_together = ('customer', 'product', 'interaction_type')
        ordering = ['-timestamp']

 

class RecommendationInteraction(models.Model):

    INTERACTION_TYPES = [
        ('exposed', 'Exposed'),
        ('viewed', 'Viewed'),
        ('clicked', 'Clicked'),
        ('dismissed', 'Dismissed'),
        ('accepted', 'Accepted'),
        ('converted', 'Converted'),
    ]

    CHANNELS = [
        ('crm', 'CRM'),
        ('whatsapp', 'WhatsApp'),
        ('call', 'Call'),
        ('app', 'App'),
        ('email', 'Email'),
    ]

    recommendation = models.ForeignKey(
        'PestRecommendation',
        on_delete=models.CASCADE,
        related_name='interactions'
    )

    customer = models.ForeignKey(
        customer_details,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    service_id = models.BigIntegerField(null=True, blank=True)

    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES
    )

    interaction_channel = models.CharField(
        max_length=20,
        choices=CHANNELS
    )

    event_time = models.DateTimeField()

    exposure_id = models.CharField(
        max_length=64,
        null=True,
        blank=True
    )

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'recommendation_interactions'
        indexes = [
            models.Index(fields=['recommendation', 'interaction_type']),
            models.Index(fields=['customer', 'event_time']),
            models.Index(fields=['interaction_type', 'event_time']),
        ]


# recommender/models.py
from django.db import models
from crmapp.models import customer_details, Product, ServiceCatalog


from django.db import models
from django.utils import timezone

from django.db import models


from django.db import models


class PestRecommendation(models.Model):

    # =========================
    # NORMALIZATION
    # =========================
    CANONICAL_TYPES = {
        "upsell": "upsell",
        "crosssell": "crosssell",
        "content": "content",
        "collaborative": "collaborative",
        "demographic": "demographic",
    }

    RECOMMENDATION_TYPES_CHOICES = [
        ("upsell", "Upsell"),
        ("crosssell", "Cross-sell"),
        ("content", "Content-Based"),
        ("collaborative", "Collaborative"),
        ("demographic", "Demographic"),
    ]

    # =========================
    # CUSTOMER
    # =========================
    customer = models.ForeignKey(
        "crmapp.customer_details",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pest_recommendations",
        db_column="customer_fk",
    )

    external_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column="customer_id",
    )

    canonical_customer_id = models.BigIntegerField(null=True, blank=True)

    # =========================
    # PRODUCT / SERVICE
    # =========================
    base_product = models.ForeignKey(
        "crmapp.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="base_recommendations",
        db_column="base_product_id",
    )

    recommended_product = models.ForeignKey(
        "crmapp.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommended_products",
    )

    recommended_service = models.ForeignKey(
        "crmapp.ServiceCatalog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommended_services",
    )

    # =========================
    # RECOMMENDATION META
    # =========================
    recommendation_type = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TYPES_CHOICES,
        null=True,
        blank=True,
    )

    business_intent = models.CharField(
        max_length=20,
        choices=[
            ("upsell", "Upsell"),
            ("crosssell", "Cross-sell"),
            ("retention", "Retention"),
            ("reactivation", "Reactivation"),
        ],
        null=True,
        blank=True,
    )

    reco_channel = models.CharField(
        max_length=20,
        choices=[("product", "Product"), ("service", "Service")],
        default="product",
    )

    algorithm_strategy = models.CharField(max_length=30, null=True, blank=True)
    model_source = models.CharField(max_length=100, null=True, blank=True)

    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.50
    )
    final_score = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.000
    )
    priority = models.IntegerField(default=100)

    # =========================
    # SERVING LIFECYCLE
    # =========================
    serving_state = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("served", "Served"),
            ("exposed", "Exposed"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
        default="pending",
    )

    served_at = models.DateTimeField(null=True, blank=True)
    shown_at = models.DateTimeField(null=True, blank=True)

    valid_from = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    # =========================
    # CHANNEL + CONSENT
    # =========================
    allowed_channels = models.JSONField(default=list, blank=True)

    consent_call = models.BooleanField(default=False)
    consent_whatsapp = models.BooleanField(default=False)
    consent_email = models.BooleanField(default=False)

    # =========================
    # CONVERSION TRACKING
    # =========================
    converted_product = models.ForeignKey(
        "crmapp.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_recommendations",
    )

    converted_service = models.ForeignKey(
        "crmapp.ServiceCatalog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_service_recommendations",
    )

    converted_at = models.DateTimeField(null=True, blank=True)

    revenue_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # =========================
    # STATE FLAGS
    # =========================
    is_active = models.BooleanField(default=False)

    action = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("help", "Help Requested"),
        ],
        default="none",
    )

    experiment_group = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C")],
        default="A",
    )

    exposure_channel = models.CharField(max_length=20, null=True, blank=True)
    exposure_id = models.CharField(max_length=64, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =========================
    class Meta:
        db_table = "pest_recommendations"

    def __str__(self):
        return f"{self.recommendation_type or 'unknown'} → {self.external_customer_id or 'NA'}"

    # =========================
    # NORMALIZATION LOGIC
    # =========================
    @staticmethod
    def normalize_recommendation_type(val):
        if not val:
            return None
        v = str(val).lower().replace("-", "").replace("_", "").replace(" ", "")
        if "up" in v and "sell" in v:
            return "upsell"
        if "cross" in v and "sell" in v:
            return "crosssell"
        if "content" in v:
            return "content"
        if "collaborative" in v:
            return "collaborative"
        if "demo" in v:
            return "demographic"
        return None

    def save(self, *args, **kwargs):
        normalized = self.normalize_recommendation_type(self.recommendation_type)
        if normalized:
            self.recommendation_type = normalized

        if not self.business_intent and normalized in ("upsell", "crosssell"):
            self.business_intent = normalized

        super().save(*args, **kwargs)

# ... (other models unchanged) ...
class HybridRankingDebug(models.Model):
    customer = models.ForeignKey(
        customer_details,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    num_candidates = models.IntegerField(default=0)
    debug_log = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "hybrid_ranking_debug"

    def __str__(self):
        return f"Hybrid Debug - {self.customer_id} ({self.generated_at})"

 

from django.db import models
from crmapp.models import customer_details, Product

class RecommendationLog(models.Model):

    ACTIONS = (
        ("shown", "Shown"),
        ("clicked", "Clicked"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    recommendation_type = models.CharField(max_length=30)  # cf / rule / hybrid / demographic
    action = models.CharField(max_length=20, choices=ACTIONS)

    score = models.FloatField(null=True, blank=True)
    position = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer", "product"]),
            models.Index(fields=["recommendation_type"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.customer_id} - {self.product_id} - {self.action}"


class CustomerProductSignal(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    purchase_count = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_purchased_at = models.DateTimeField(null=True, blank=True)

    recency_score = models.FloatField(default=0)
    frequency_score = models.FloatField(default=0)
    monetary_score = models.FloatField(default=0)

    class Meta:
        unique_together = ("customer", "product")
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["product"]),
        ]
class CustomerServiceSignal(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)
    service = models.ForeignKey(service_management, on_delete=models.CASCADE)

    total_contract_value = models.DecimalField(max_digits=12, decimal_places=2)
    contract_type = models.CharField(max_length=50)
    contract_status = models.CharField(max_length=20)

    last_service_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("customer", "service")

class Recommendation(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    service = models.ForeignKey(
        service_management,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    method = models.CharField(
        max_length=30,
        choices=[
            ("cf", "Collaborative"),
            ("content", "Content Based"),
            ("upsell", "Upsell"),
            ("cross_sell", "Cross Sell"),
            ("demographic", "Demographic"),
            ("hybrid", "Hybrid"),
        ]
    )

    score = models.FloatField()
    rank = models.IntegerField()

    reason = models.TextField()
    model_version = models.CharField(max_length=50)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["method"]),
        ]

class RecommendationEvent(models.Model):
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE
    )

    event_type = models.CharField(
        max_length=20,
        choices=[
            ("shown", "Shown"),
            ("clicked", "Clicked"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ]
    )

    event_time = models.DateTimeField(auto_now_add=True)

class RecommendationRun(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)

    engines_used = models.JSONField()
    weights = models.JSONField()

    candidate_count = models.IntegerField()
    final_count = models.IntegerField()

    model_version = models.CharField(max_length=50)
    run_time_ms = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)



class MLModelRegistry(models.Model):
    name = models.CharField(max_length=50)
    version = models.CharField(max_length=50)
    path = models.CharField(max_length=255)

    trained_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)


# recommender/models.py

class MessageDeliveryLog(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)
    recommendation = models.ForeignKey(
        PestRecommendation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    channel = models.CharField(max_length=20)  # whatsapp / email
    recipient = models.CharField(max_length=255)

    message = models.TextField()

    provider = models.CharField(max_length=50, default="rapbooster")
    provider_message_id = models.CharField(max_length=255, null=True, blank=True)

    provider_status = models.CharField(max_length=50)
    raw_response = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_delivery_log"
        indexes = [
            models.Index(fields=["customer", "channel"]),
            models.Index(fields=["provider_message_id"]),
        ]


# models.py
class MessageLog(models.Model):
    CHANNELS = (
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
    )

    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE)
    channel = models.CharField(max_length=20, choices=CHANNELS)
    template = models.ForeignKey(
        MessageTemplates, null=True, blank=True, on_delete=models.SET_NULL
    )

    message_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, default="queued")

    provider_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
