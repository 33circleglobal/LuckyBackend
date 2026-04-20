from rest_framework.response import Response
from rest_framework import status


def _extract_error_message(error):
    """
    Safely extract error message from DRF ValidationError or any exception
    """
    print(error)
    if hasattr(error, "detail"):
        detail = error.detail

        if isinstance(detail, list):
            return str(detail[0])

        if isinstance(detail, dict):
            for key, value in detail.items():
                if isinstance(value, list) and value:
                    return str(value[0])
                elif isinstance(value, dict):
                    return _extract_error_message(value)
            return str(detail)

        return str(detail)

    return str(error)


def api_response(
    *,
    message=None,
    data=None,
    error=None,
    status_code=status.HTTP_200_OK,
    error_code=None,
    pagination=None
):
    """
    Standard API response wrapper
    """

    response = {
        "success": status_code < 400,
        "message": message if status_code < 400 else None,
        "error": error if status_code >= 400 else None,
        "data": data,
    }

    # Optional error code (useful for frontend handling)
    if error_code:
        response["error_code"] = error_code

    # Optional pagination support
    if pagination:
        response["pagination"] = pagination

    return Response(response, status=status_code)


# ✅ SUCCESS RESPONSE
def success_response(message="Success", data=None, status_code=status.HTTP_200_OK):
    return api_response(message=message, data=data, status_code=status_code)


# ❌ GENERIC FAILURE RESPONSE
def failed_response(
    message="Something went wrong", data=None, status_code=status.HTTP_400_BAD_REQUEST
):
    return api_response(error=message, data=data, status_code=status_code)


# ⚠️ VALIDATION ERROR RESPONSE
def validation_failed_response(
    error, data=None, status_code=status.HTTP_400_BAD_REQUEST
):
    error_message = _extract_error_message(error)

    return api_response(error=error_message, data=data, status_code=status_code)
