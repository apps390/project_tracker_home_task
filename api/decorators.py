from functools import wraps
from rest_framework import status
from project_tracker.utils.response_handler import build_response


def manager_required(view_func):
    """Ensure the user is authenticated and has role='manager'."""
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        user = request.user

        if not getattr(user, "is_authenticated", False):
            return build_response(False, errors="Authentication required.", status_code=status.HTTP_401_UNAUTHORIZED)
        
        if getattr(user, "role", None) != "manager":
            return build_response(False, errors="Access denied. Only project managers are allowed.", status_code=status.HTTP_403_FORBIDDEN)
        
        return view_func(self, request, *args, **kwargs)

    return _wrapped_view
