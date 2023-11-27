import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request information
        logger.info(f"API Request :{request}, Method: {request.method}, Path: {request.path}, Body: {request.body}")

        response = self.get_response(request)

        # Log response information
        logger.info(f"Status Code: {response.status_code}")
        return response
