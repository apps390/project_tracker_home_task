from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from .models import Project, Task
from project_tracker import settings
import logging

logger = logging.getLogger('tracker_logger')
User = get_user_model()

@shared_task
def check_project_overdue():
    """
    Check for projects that are past their end_date and mark them as overdue
    Send notifications to created_by and members
    """
    try:
        today = timezone.now().date()
        overdue_projects = Project.objects.filter(
            end_date__lt=today,
            status__in=['active', 'on_hold'],
            is_deleted=False
        )
        
        for project in overdue_projects:
            # Update project status to overdue
            project.status = 'overdue'
            project.save(update_fields=['status', 'updated_at'])
            
            # Send notifications
            send_project_overdue_notification.delay(project.id)
            
        logger.info(f"Checked project overdue status. Found {overdue_projects.count()} overdue projects.")
        return f"Processed {overdue_projects.count()} overdue projects"
        
    except Exception as e:
        logger.error(f"Error in check_project_overdue: {str(e)}")
        raise

@shared_task
def send_project_overdue_notification(project_id):
    """
    Send HTML email notification for overdue project
    """
    try:
        project = Project.objects.get(id=project_id, is_deleted=False)
        
        # Get recipients - project creator and all members
        recipients = [project.created_by.email]
        members_emails = project.members.values_list('user__email', flat=True)
        recipients.extend(members_emails)
        
        # Remove duplicates and None values
        recipients = list(set([email for email in recipients if email]))
        
        subject = f"Project Overdue: {project.name}"
        
        # Create HTML email content
        context = {
            'project_name': project.name,
            'end_date': project.end_date,
            'today': timezone.now().date(),
        }
        
        html_message = render_to_string('project_overdue_notification.html', context)
        
        # Send HTML-only email
        send_mail(
            subject=subject,
            message=f"Project {project.name} is overdue as of {timezone.now().date()}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent HTML overdue notification for project '{project.name}' to {len(recipients)} recipients")
        
    except Project.DoesNotExist:
        logger.error(f"Project with id {project_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending project overdue notification: {str(e)}")
        raise

@shared_task
def check_task_overdue():
    """
    Check for tasks that are due today or overdue
    Send notifications and update status
    """
    try:
        today = timezone.now().date()
        
        # Tasks due today
        tasks_due_today = Task.objects.filter(
            due_date=today,
            status__in=['ongoing', 'on_hold'],
            is_deleted=False
        )
        
        # Tasks that are overdue
        overdue_tasks = Task.objects.filter(
            due_date__lt=today,
            status__in=['ongoing', 'on_hold'],
            is_deleted=False
        )
        
        # Update overdue tasks status
        overdue_tasks.update(status='overdue')
        
        # Send notifications for tasks due today
        for task in tasks_due_today:
            send_task_due_today_notification.delay(task.id)
        
        # Send notifications for overdue tasks
        for task in overdue_tasks:
            send_task_overdue_notification.delay(task.id)
            
        logger.info(f"Checked task due dates. {tasks_due_today.count()} due today, {overdue_tasks.count()} overdue")
        return f"Processed {tasks_due_today.count()} due today, {overdue_tasks.count()} overdue"
        
    except Exception as e:
        logger.error(f"Error in check_task_overdue: {str(e)}")
        raise

@shared_task
def send_task_due_today_notification(task_id):
    """
    Send HTML notification for tasks due today
    """
    try:
        task = Task.objects.get(id=task_id, is_deleted=False)
        
        recipients = list(task.assigned_to.values_list('user__email', flat=True))
        recipients.append(task.project.created_by.email)
        
        recipients = list(set([email for email in recipients if email]))
        
        subject = f"Task Due Today: {task.title}"
        
        context = {
            'task_title': task.title,
            'project_name': task.project.name,
            'due_date': task.due_date,
        }
        
        html_message = render_to_string('task_due_today_notification.html', context)
        
        # Send HTML-only email
        send_mail(
            subject=subject,
            message=f"Task {task.title} is ovedue as of {timezone.now().date()}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent HTML due today notification for task '{task.title}' to {len(recipients)} recipients")
        
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending task due today notification: {str(e)}")
        raise

@shared_task
def send_task_overdue_notification(task_id):
    """
    Send HTML notification for overdue tasks
    """
    try:
        task = Task.objects.get(id=task_id, is_deleted=False)
        
        # Get recipients - assigned users and project manager
        recipients = list(task.assigned_to.values_list('user__email', flat=True))
        recipients.append(task.project.created_by.email)
        
        # Remove duplicates and None values
        recipients = list(set([email for email in recipients if email]))
        
        subject = f"Task Overdue: {task.title}"
        
        context = {
            'task_title': task.title,
            'project_name': task.project.name,
            'due_date': task.due_date,
            'days_overdue': (timezone.now().date() - task.due_date).days,
        }
        
        html_message = render_to_string('task_overdue_notification.html', context)
        
        # Send HTML-only email
        send_mail(
            subject=subject,
            message =f"Task {task.title} is ovedue as of {timezone.now().date()}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Sent HTML overdue notification for task '{task.title}' to {len(recipients)} recipients")
        
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending task overdue notification: {str(e)}")
        raise

@shared_task
def check_daily_notifications():
    """
    Master task that runs all daily checks
    """
    try:
        check_project_overdue.delay()
        check_task_overdue.delay()
        logger.info("Daily notification checks completed")
    except Exception as e:
        logger.error(f"Error in daily notifications: {str(e)}")
        raise