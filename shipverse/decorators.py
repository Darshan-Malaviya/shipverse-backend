from functools import wraps
import logging
from .models import *
from .auth import *
from .response import func_response
from rest_framework import status

logger = logging.getLogger(__name__)

# def log_api_activity(func):
#     @wraps(func)
#     def wrapper(request, *args, **kwargs):
#     #     # if isinstance(request, HttpRequest):
#     #         # logger.info(f"API Request, Path: {request.path}, Body: {request.body}")
#         return func(request, *args, **kwargs)
#     return wrapper


def authenticate_user(func):
    @wraps(func)    
    def wrapper(self, request, *args, **kwargs):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
                user = Users.objects.get(id=user_id, isEmailVerified=True)
                request.user = user
            except:
                return func_response("failed", "User not found.", status.HTTP_400_BAD_REQUEST)
            return func(self, request, *args, **kwargs)
        else:
            return func_response("failed", "Unauthorized token.", status.HTTP_400_BAD_REQUEST)
    return wrapper

def validate_token(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        token_id = request.data.get("tokenId")
        if not token_id:
            return func_response("failed", "Token id not found!", status.HTTP_400_BAD_REQUEST)
        return func(self, request, *args, **kwargs)
    return wrapper