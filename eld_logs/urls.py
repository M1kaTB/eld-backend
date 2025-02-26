from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, LogEntryViewSet

router = DefaultRouter()
router.register(r'trips', TripViewSet)
router.register(r'logs', LogEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
