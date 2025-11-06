from rest_framework.response import Response
from rest_framework import status


def build_response(success=True, message=None, errors=None, data=None, status_code=None):
    """
    Unified API response format.
    Returns a minimal but clear structure:
    - On success: success, message, data (optional)
    - On error: success=False, message=first error
    """
    if success:
        response_data = {
            "success": True,
            "message": message or "Request completed successfully",
        }
        if data is not None:
            response_data["data"] = data
        return Response(response_data, status=status_code or status.HTTP_200_OK)

    if isinstance(errors, dict):
        first_error = next(iter(errors.values()))[0]
    elif isinstance(errors, list):
        first_error = errors[0]
    else:
        first_error = str(errors) or "Something went wrong"

    return Response(
        {
            "success": False,
            "message": first_error,
            **({"data": data} if data else {}), 
        },
        status=status_code or status.HTTP_400_BAD_REQUEST,
    )
