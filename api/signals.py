import threading
import logging
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Project, Task, Contributor

logger = logging.getLogger('tracker_logger')


def _clear_project_cache(project):
    """Internal helper to clear cache related to a project and its members."""
    try:
        user_id = project.created_by.id
        # Clear project list cache
        cache.delete_pattern(f"project_list:{user_id}:*")
        logger.info(f"Cache cleared for Project creator: {user_id}")

        # Clear task list cache for this project
        cache.delete_pattern(f"task_list:*:{project.slug}:*")
        logger.info(f"Task cache cleared for project: {project.slug}")

        # Clear cache for all project members
        member_ids = project.members.values_list("user__id", flat=True)
        for member_id in member_ids:
            cache.delete_pattern(f"project_list:{member_id}:*")
            logger.info(f"Cache cleared for member: {member_id}")

    except Exception as e:
        logger.error(f"Error clearing cache for project '{project.slug}': {e}", exc_info=True)


def clear_project_cache_async(project):
    """Runs cache invalidation in a background thread."""
    threading.Thread(target=_clear_project_cache, args=(project,)).start()


@receiver([post_save, post_delete], sender=Project)
def project_cache_handler(sender, instance, **kwargs):
    logger.debug(f"Signal: Project change detected -> {instance.slug}")
    clear_project_cache_async(instance)


@receiver([post_save, post_delete], sender=Task)
def task_cache_handler(sender, instance, **kwargs):
    logger.debug(f"Signal: Task change detected -> {instance.slug}")
    clear_project_cache_async(instance.project)


@receiver([post_save, post_delete], sender=Contributor)
def contributor_cache_handler(sender, instance, **kwargs):
    logger.debug(f"Signal: Contributor change detected -> {instance.user.email}")
    for project in instance.projects.all():
        clear_project_cache_async(project)


@receiver(m2m_changed, sender=Project.members.through)
def project_membership_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.debug(f"Signal: Project members updated -> {instance.slug}")
        clear_project_cache_async(instance)