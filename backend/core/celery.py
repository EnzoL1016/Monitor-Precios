import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # <--- CLAVE

app = Celery('scraper_project')

# El namespace='CELERY' obliga a que en settings.py las variables empiecen con CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()