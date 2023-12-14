from rest_framework.views import APIView
from .auth import getUserIdByToken
from .models import Users, CandapostUserDetails
from rest_framework.response import Response
import base64
import requests
from rest_framework import status
import xmltodict
from .common import add_carrier_user
import os
import json
from .serializers import UserCarrierSerializer, CanadaPostPriceSerializer, UserCarrier

class canada_users_account_details(APIView):

    def post(self,request) :
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        print(auth_header)
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        if not user :
            return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
        
        serializer = UserCarrierSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors)
        
        if(request.data['carrier']):
            # url = "https://soa-gw.canadapost.ca/ot/token"
            url = "https://ct.soa-gw.canadapost.ca/ot/token"
            cred = base64.b64encode(str(os.environ.get("canadapost_username_debug") + ":" + os.environ.get("canadapost_password_debug")).encode("ascii"))
            result = requests.post(url=url,data=None,headers={
                "Accept":"application/vnd.cpc.registration-v2+xml",
                "Content-Type":"application/vnd.cpc.registration-v2+xml",
                "Authorization":"Basic "+ cred.decode("ascii"),
                "Accept-language":"en-CA"
            })
            json_decoded = xmltodict.parse(result.content)
            token_id = json_decoded["token"]["token-id"]
            # redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/merchant"
            redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
            if(result.status_code == 200):
                user_carrier = add_carrier_user(user, request.data, token_id=token_id)
                response = {
                    "isSuccess":True,
                    "message":None,
                    "data":{
                        # "redirectUrl":redirect_url+"?token-id="+json_decoded["token"]["token-id"]+"&platform-id="+str(user_carrier.id)+"&return-url=https://dev1.goshipverse.com/cpVerify"
                         "redirectUrl":redirect_url+"?token-id="+json_decoded["token"]["token-id"]+"&platform-id="+str(user_carrier.id)+"&return-url=https://d2cd-2405-201-2017-30e4-e77a-6f83-e507-d794.ngrok-free.app/verifyCP"
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
    

class VerifyCanadaPost(APIView):
    def post(self, request):
        token_id = request.data["tokenId"]
        print("token id ", token_id)
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        if not user: 
            return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)    
        url = "https://ct.soa-gw.canadapost.ca/ot/token/"+token_id
        # url = "https://soa-gw.canadapost.ca/ot/token/"+token_id
        cred = base64.b64encode(str(os.environ.get("canadapost_username_debug") + ":" + os.environ.get("canadapost_password_debug")).encode("ascii"))
        result = requests.get(url=url,headers={
            "Accept":"application/vnd.cpc.registration-v2+xml",
            "Content-Type":"application/vnd.cpc.registration-v2+xml",
            "Authorization":"Basic "+ cred.decode("ascii"),
            "Accept-language":"en-CA"
        })
        json_decoded = xmltodict.parse(result.content)
        print("json_decoded -----> ",json_decoded)

        print(type(json_decoded))

        # mydict = json.loads(json_decoded)

        customer_number = json_decoded.get("merchant-info").get("customer-number")
        contract_number = json_decoded.get("merchant-info").get("contract-number")
        merchant_username = json_decoded.get("merchant-info").get("merchant-username")
        merchant_password = json_decoded.get("merchant-info").get("merchant-password")
        is_credit_card = json_decoded.get("merchant-info").get("has-default-credit-card")

        if(result.status_code == 200):

            user_carrier = UserCarrier.objects.filter(token_id = token_id)[0]
            
            candapost_obj = CandapostUserDetails(
                            customer_number = customer_number,
                            contract_number = contract_number,
                            merchant_username = merchant_username,
                            merchant_password = merchant_password,
                            has_credit_card = is_credit_card,
                            usercarrier_id = user_carrier.id)

            candapost_obj.save()
            print(candapost_obj)

            response = {
                "isSuccess":True,
                "message":"",
                "data":json_decoded["merchant-info"]
            }
            
        else:
            response = {
                "isSuccess":False,
                "message":json_decoded["messages"]["message"],
                "data":None
            }
        return Response(response,status=status.HTTP_200_OK)


class CanadaPostPrice(APIView):

    def post(self, request):
        # auth_header = request.META.get('HTTP_AUTHORIZATION')
        # user_id = getUserIdByToken(auth_header)
        # user = Users.objects.get(id=user_id)

        serializers = CanadaPostPriceSerializer(data=request.data)
        if not serializers.is_valid():
            return Response(data=serializers.errors, status=status.HTTP_400_BAD_REQUEST)
        
        origin_postal_code = request.data.get("origin_postal_code")
        postal_code = request.data.get("postal_code")
        weight = request.data.get("weight")
        # if not user : 
        #     return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)    
        
        url = "https://ct.soa-gw.canadapost.ca/rs/ship/price"
        cred = base64.b64encode(str(os.environ.get("canadapost_username_debug") + ":" + os.environ.get("canadapost_password_debug")).encode("ascii"))
        headers={
            "Accept":"application/vnd.cpc.ship.rate-v4+xml",
            "Content-Type":"application/vnd.cpc.ship.rate-v4+xml",
            "Authorization":"Basic "+ cred.decode("ascii"),
            "Accept-language":"en-CA"
        }

        xml_content = """
            <mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
            <customer-number>0006006116</customer-number>
            <parcel-characteristics>
            <weight>{}</weight>
            </parcel-characteristics>
            <origin-postal-code>{}</origin-postal-code>
            <destination>
            <domestic>
            <postal-code>{}</postal-code>
            </domestic>
            </destination>
            </mailing-scenario>
            """.format(weight,origin_postal_code, postal_code)
        
        response = requests.post(url=url,
                                data=xml_content,
                                headers=headers)
        
        json_decoded = xmltodict.parse(response.content)
        service1 = json_decoded["price-quotes"]["price-quote"][0]
        service2 = json_decoded["price-quotes"]["price-quote"][1]
        service3 = json_decoded["price-quotes"]["price-quote"][2]
        service4 = json_decoded["price-quotes"]["price-quote"][3]
        response = {
            service1["service-name"]: service1["price-details"]["base"],
            service2["service-name"]: service2["price-details"]["base"],
            service3["service-name"]: service3["price-details"]["base"],
            service4["service-name"]: service4["price-details"]["base"]
        }
        
        return Response(data=response, status=status.HTTP_200_OK)