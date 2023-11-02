from rest_framework.exceptions import APIException


class ResourceNotFoundException(APIException):
    status_code = 404
    default_detail = 'Resource not found.'
    default_code = 'resource_not_found'
