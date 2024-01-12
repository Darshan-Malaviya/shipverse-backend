from rest_framework.response import Response
from rest_framework import status

def func_response(result, data):
    return Response({
        "result": result,
        "data": data,
    })