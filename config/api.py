from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(data=None, message='OK', status_code=status.HTTP_200_OK):
    return Response(
        {
            'success': True,
            'message': message,
            'data': data,
        },
        status=status_code,
    )


def error_response(
    message='Request failed.',
    *,
    errors=None,
    code='request_failed',
    status_code=status.HTTP_400_BAD_REQUEST,
):
    return Response(
        {
            'success': False,
            'message': message,
            'code': code,
            'errors': errors,
        },
        status=status_code,
    )


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    message = 'Request failed.'
    errors = None

    if isinstance(detail, dict):
        if 'detail' in detail and isinstance(detail['detail'], str):
            message = detail['detail']
            errors = None
        else:
            message = 'Request validation failed.'
            errors = detail
    elif isinstance(detail, list):
        message = 'Request validation failed.'
        errors = detail
    elif isinstance(detail, str):
        message = detail

    response.data = {
        'success': False,
        'message': message,
        'code': f'http_{response.status_code}',
        'errors': errors,
    }
    return response
