import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_tracker.settings')

app = Celery('project_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-daily-notifications-midnight': {
        'task': 'api.tasks.check_daily_notifications',
        'schedule': crontab(minute='*/2'),  # Daily at midnight
    },
}

app.conf.timezone =  'Asia/Kolkata'