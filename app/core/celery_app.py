from celery import Celery
from celery.schedules import crontab
from app.core.config import Config

celery_app = Celery(
    'mangafire',
    broker=Config.broker_url,
    backend=Config.result_backend
)
celery_app.conf.task_always_eager = Config.task_always_eager

# Auto-discover tasks so they are registered when celery starts
celery_app.autodiscover_tasks(['app.tasks'])

celery_app.conf.beat_schedule = {
    'check-manga-updates-every-hour': {
        'task': 'app.tasks.scraper_tasks.auto_downloader_cron',
        'schedule': crontab(minute=0), # Run every hour at minute 0
    },
}

def make_celery(app):
    celery_app.conf.update(app.config)

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app
