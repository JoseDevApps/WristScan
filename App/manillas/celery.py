import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "manillas.settings")

celery_app = Celery("manillas")

# Load Celery config from Django settings
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed Django apps
celery_app.autodiscover_tasks()

@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
