from django.urls import path
from rest_framework.routers import DefaultRouter

from app.api.legal import PrivacyPolicyView, TermsOfServiceView
from app.api.webhook import UserViewSet, WebhookView, health_view

router = DefaultRouter()
router.register("user", UserViewSet, basename="user")

urlpatterns = [
    path("webhook/", WebhookView.as_view(), name="webhook"),
    path("health_check/", health_view, name="health_check"),
    path("privacy-policy/", PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("terms-of-service/", TermsOfServiceView.as_view(), name="terms_of_service"),
]

urlpatterns += router.urls