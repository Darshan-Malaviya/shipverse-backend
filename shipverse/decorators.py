from functools import wraps
from django.http import HttpRequest
import logging

logger = logging.getLogger(__name__)

def log_api_activity(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if isinstance(request, HttpRequest):
            logger.info(f"API Request, Path: {request.path}, Body: {request.body}")
        return func(request, *args, **kwargs)
    return wrapper
