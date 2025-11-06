import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
# Celery Beat Schedule
app.conf.beat_schedule = {
    'check-daily-notifications-midnight': {
        'task': 'api.tasks.check_daily_notifications',
        'schedule': crontab(hour=0, minute=0),  # Run daily at 12:00 AM (midnight)
    },
    'check-project-overdue-1am': {
        'task': 'api.tasks.check_project_overdue',
        'schedule': crontab(hour=1, minute=0),  # Run daily at 1:00 AM
    },
    'check-task-overdue-1am': {
        'task': 'api.tasks.check_task_overdue',
        'schedule': crontab(hour=1, minute=0),  # Run daily at 1:00 AM
    },
}
app.conf.timezone =  'Asia/Kolkata'