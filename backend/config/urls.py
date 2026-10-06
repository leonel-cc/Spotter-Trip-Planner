from django.urls import path
from django.views.generic import TemplateView
from trips.views import health, locations, plan_trip

urlpatterns = [
    path("api/health", health),
    path("api/locations", locations),
    path("api/trips/plan", plan_trip),
    path("", TemplateView.as_view(template_name="index.html")),
]
