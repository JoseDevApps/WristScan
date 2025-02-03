from django.urls import path
from .views import create_event, event_detail

urlpatterns = [
    path("", create_event, name="create_event"),
    path("event/<int:event_id>/", event_detail, name="event_detail"),
]