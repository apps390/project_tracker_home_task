from project_tracker.utils.response_handler import build_response
from rest_framework import status
import logging

logger = logging.getLogger('tracker_logger')

def validate_project_access(project, user, action="perform this action"):
    """
    Validates whether the user is allowed to perform an action on a project.
    
    Returns:
        Response (if invalid)
        None (if valid)
    """
    # Check if user is the creator of the project
    if project.created_by != user:
        logger.warning(f"Unauthorized attempt by {user.email} to {action} on project '{project.name}'")
        return build_response(False,errors=f"You are not authorized to {action} on this project.",status_code=status.HTTP_403_FORBIDDEN,)

    if getattr(project, "is_deleted", False):
        logger.warning(f"Attempt to {action} on deleted project '{project.name}' by {user.email}")
        return build_response(False,errors="This project has already been deleted.",status_code=status.HTTP_400_BAD_REQUEST,)

    return None


def validate_project_member_access(project, user, action="access this project"):
    """
    Validates whether the user can access or act on a project.
    This includes:
      - The project creator (manager)
      - Any valid contributor (member)
    """

    # Check if the project is deleted
    if getattr(project, "is_deleted", False):
        logger.warning(f"Attempt to {action} on deleted project '{project.name}' by {user.email}")
        return build_response(
            False,
            errors="This project has already been deleted.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Allow if the user is the manager (project creator)
    if project.created_by == user:
        return None

    # Allow if user is a contributor (member)
    if hasattr(user, "contributor_profile"):
        contributor = user.contributor_profile
        if project.members.filter(id=contributor.id).exists():
            return None 

    # Otherwise, deny access
    logger.warning(f"Unauthorized attempt by {user.email} to {action} on project '{project.name}'")
    return build_response(False, errors=f"You are not authorized to {action} on this project.",status_code=status.HTTP_403_FORBIDDEN)
