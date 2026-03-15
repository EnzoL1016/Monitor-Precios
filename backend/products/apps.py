from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """
        Se ejecuta cuando Django termina de cargar todas las apps.
        Registra el scheduler para correr en el mismo proceso (sin workers separados).
        """
        import os
        import sys

        # En desarrollo con runserver, Django lanza 2 procesos:
        # - El watcher (sin RUN_MAIN): recarga módulos al detectar cambios
        # - El servidor real (RUN_MAIN='true'): sirve requests
        # Solo iniciamos el scheduler en el proceso servidor real para evitar duplicados.
        # En producción (Gunicorn), no hay reloader → siempre iniciamos.
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        self._start_scheduler()

    def _start_scheduler(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from django_apscheduler.jobstores import DjangoJobStore
        from products.tasks import update_all_products_prices
        import logging

        logger = logging.getLogger(__name__)

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        scheduler.add_job(
            update_all_products_prices,
            trigger=IntervalTrigger(hours=1),
            id='update_all_products_prices',
            name='Scraping automático de precios cada hora',
            replace_existing=True,
            max_instances=1,        # Evita que se solapen ejecuciones
            misfire_grace_time=600  # 10 min de tolerancia si el servidor estaba durmiendo
        )

        try:
            scheduler.start()
            logger.info("[Scheduler] APScheduler iniciado. Scraping automático cada hora.")
        except Exception as e:
            logger.error(f"[Scheduler] Error al iniciar APScheduler: {e}")
