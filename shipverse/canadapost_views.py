from rest_framework.views import APIView
from .auth import getUserIdByToken
from .models import Users
from rest_framework.response import Response
import base64
import requests
from django.conf import settings
from rest_framework import status
import xmltodict
from .common import add_carrier_user

class CanadaPostAccount(APIView):

    def post(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        user_id = getUserIdByToken(auth_header)

        user = Users.objects.get(id=user_id)
        if not user : 
            return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
        
        if(request.data['carrier']):
            url = "https://soa-gw.canadapost.ca/ot/token"
            cred = base64.b64encode(str(settings.CANADAPOST_USERNAME + ":" + settings.CANADAPOST_PASSWORD).encode("ascii"))
            result = requests.post(url=url,data=None,headers={
                "Accept":"application/vnd.cpc.registration-v2+xml",
                "Content-Type":"application/vnd.cpc.registration-v2+xml",
                "Authorization":"Basic "+ cred.decode("ascii"),
                "Accept-language":"en-CA"
            })
            json_decoded = xmltodict.parse(result.content)
            redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/merchant"
            if(result.status_code == 200):
                user_carrier = add_carrier_user(user, request.data)
                response = {
                    "isSuccess":True,
                    "message":None,
                    "data":{
                        "redirectUrl":redirect_url+"?token-id="+json_decoded["token"]["token-id"]+"&platform-id="+str(user_carrier.id)+"&return-url=https://dev1.goshipverse.com/cpVerify"
                    }
                }
            else:
                response = {
                    "isSuccess":False,
                    "message":json_decoded["messages"]["message"],
                    "data":None
                }
            return Response(response,status=status.HTTP_200_OK)
        else:
            add_carrier_user(user, request.data)
        return Response({},status=status.HTTP_200_OK)
    

