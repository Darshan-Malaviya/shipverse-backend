import requests
import os, io
import xmltodict
import base64
import fitz  # PyMuPDF
from rest_framework import status
from django.http import HttpResponse
from .auth import getUserIdByToken
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Users, CandapostUserDetails, UserCarrier
from .common import add_carrier_user
from .serializers import UserCarrierSerializer, CanadaPostPriceSerializer
import shipverse.constant as const
from shipverse.models import *
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse

from .utils import *


class CanadaUsersAccountDetails(APIView):
    """
    Step1 -  Create canada post account.

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized or Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            
            serializer = UserCarrierSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors)

            if request.data["carrier"]:
                url = f"https://{const.canadaPost}/ot/token"
                result = requests.post(
                    url=url,
                    data=None,
                    headers={
                        "Accept": const.contentTypeRegistrationXml,
                        "Content-Type": const.contentTypeRegistrationXml,
                        "Authorization": "Basic " + const.encoded_cred,
                        "Accept-language": const.acceptLanguage,
                    },
                )
                json_decoded = xmltodict.parse(result.content)
                token_id = json_decoded["token"]["token-id"]

                if result.status_code == 200:
                    redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
                    user_carrier = add_carrier_user(user, request.data, token_id=token_id)
                    response = {
                        "isSuccess": True,
                        "message": None,
                        "data": {
                            "redirectUrl": redirect_url
                            + "?token-id="
                            + json_decoded.get("token", {}).get("token-id")
                            + "&platform-id="
                            + str(const.customerNo)
                            + f"&return-url={const.cpVerify_link}"
                        },
                    }
                else:
                    response = {
                        "isSuccess": False,
                        "message": json_decoded.get("messages", {}).get("message"),
                        "data": None,
                    }
                return Response(response, status=status.HTTP_200_OK)
            else:
                add_carrier_user(user, request.data)
            return Response({}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Unauthorized token"}, status=status.HTTP_401_UNAUTHORIZED
            )


class VerifyCanadaPost(APIView):
    """
    Step2 - Verify the carrier account

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            token_id = request.data["tokenId"]
            if not token_id:
                return Response(
                    {"message": "Token id not found!"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            try:
                user_id = getUserIdByToken(auth_header)
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized or Invalid Token!"},
                    status=status.HTTP_200_OK,
                )

            url = f"https://{const.canadaPost}/ot/token/" + token_id
            headers = {
                "Accept": const.contentTypeRegistrationXml,
                "Content-Type": const.contentTypeRegistrationXml,
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            result = requests.get(
                url=url,
                headers=headers,
            )
            json_decoded = xmltodict.parse(result.content)
            user_carrier = UserCarrier.objects.filter(token_id = token_id)[0]

            if result.status_code == 200:
                customer_number = json_decoded.get("merchant-info").get("customer-number")
                contract_number = json_decoded.get("merchant-info").get("contract-number")
                merchant_username = json_decoded.get("merchant-info").get(
                    "merchant-username"
                )
                merchant_password = json_decoded.get("merchant-info").get(
                    "merchant-password"
                )
                is_credit_card = json_decoded.get("merchant-info").get(
                    "has-default-credit-card"
                )

                candapost_obj = CandapostUserDetails(
                    user=user,
                    customer_number=customer_number,
                    contract_number=contract_number,
                    merchant_username=merchant_username,
                    merchant_password=merchant_password,
                    has_credit_card=is_credit_card,
                    usercarrier_id = user_carrier.id
                )
                candapost_obj.save()

                response = {
                    "isSuccess": True,
                    "message": "",
                    "data": json_decoded["merchant-info"],
                }

            else:
                response = {
                    "isSuccess": False,
                    "message": json_decoded["messages"]["message"],
                    "data": None,
                }
            return Response(response, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )


class ShipmentCreateAPI(APIView):
    """
    Create shipment in Canada Post
    """

    def post(self, request):
        try:
            user = get_authenticated_user(request)
            user_carrier = UserCarrier.objects.filter(user=user).first()
            from_location = FromLocation.objects.filter(userId = user.id).first()
            # print("from loc", from_location.postalCode)
            data = request.data
            customer_no = os.environ["customer_number"]
            group_id = data.get("group_id")
            shipping_request_point = from_location.postalCode
            service_code = data.get("shipmentData", {}).get("service_code")

            sender_info = get_sender_info(user, user_carrier, from_location)
            receiver_info = get_receiver_info(data)
            parcel_info = get_parcel_info(data)

            options = get_options(data)
            notification_email = user.email
            customs_info = get_customs_info(data)

            payment_option = data.get("shipmentData", {}).get("paymentInformation", {}).get("paymentMethod")

            if not payment_option == "creditcard":
                settlement_info = {
                    "contract_id": "0044084515",
                    "intended_method_of_payment": "creditcard",
                }
            elif not payment_option == "account":
                settlement_info = {
                    "contract_id": "0044084515",
                    "intended_method_of_payment": "account",  
                }
            else:
                settlement_info = {
                    "contract_id": "0044084515",
                    "intended_method_of_payment": payment_option, 
                }

            url = f"https://{const.canadaPost}/rs/{customer_no}/{customer_no}/shipment"

            headers = {
                "Accept": "application/vnd.cpc.shipment-v8+xml",
                "Content-Type": "application/vnd.cpc.shipment-v8+xml",
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            payload = build_shipment_payload(
                group_id,
                shipping_request_point,
                service_code,
                sender_info,
                receiver_info,
                parcel_info,
                options,
                notification_email,
                customs_info,
                settlement_info,
            )   

            result = requests.post(url, headers=headers, data=payload)
            json_decoded = xmltodict.parse(result.content)

            if result.status_code == 200:
                response = {
                    "shipment-id": json_decoded.get("shipment-info", {}).get("shipment-id"),
                    "shipment-status": json_decoded.get("shipment-info", {}).get("shipment-status"),
                    "tracking-pin": json_decoded.get("shipment-info", {}).get("tracking-pin"),
                    "artifact_url": json_decoded.get("shipment-info", {}).get("links", {}).get("link", {})[-1].get("@href")
                }
            else:
                response = {
                    "shipment-id": None,
                    "shipment-status": False,
                    "tracking-pin": None,
                }
                print("json_decoded ::", json_decoded)
                return Response(json_decoded.get("message",{}).get("description"), status=status.HTTP_400_BAD_REQUEST)

            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CanadaPostPrice(APIView):
    """
    Get price form the canada post

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized or Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            # serializers = CanadaPostPriceSerializer(data=request.data)
            # if not serializers.is_valid():
            #     return Response(data=serializers.errors, status=status.HTTP_400_BAD_REQUEST)

            origin_postal_code = request.data.get("origin_postal_code")
            postal_code = request.data.get("postal_code")
            country_code = request.data.get("country_code")
            print("origin_postal_code ::", origin_postal_code)

            weight = request.data.get("weight") if request.data.get("weight") else "1"
            length = request.data.get("length")
            width = request.data.get("width") 
            height = request.data.get("height") 
            insurance_value = request.data.get("insurance_value")

            url = f"https://{const.canadaPost}/rs/ship/price"
            headers = {
                "Accept": const.contentTypeShipRateXml,
                "Content-Type": const.contentTypeShipRateXml,
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            xml_content = f"""
                            <mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
                                <customer-number>{const.customerNo}</customer-number>"""
            if insurance_value:
                xml_content+=f"""<options>
                                    <option>
                                        <option-code>COV</option-code>
                                        <option-amount>{insurance_value}</option-amount>
                                    </option>
                                <options>"""
                                
            xml_content += f""" <parcel-characteristics>
                                    <weight>{weight}</weight>"""
            if length or width or height:
                    xml_content+=f"""           
                                    <dimensions>
                                        <length>{length}</length>
                                        <width>{width}</width>
                                        <height>{height}</height>
                                    </dimensions>"""
            xml_content += f"""
                                </parcel-characteristics>
                                <origin-postal-code>{origin_postal_code.replace(" ","")}</origin-postal-code>
                                """
            if country_code:
                xml_content += f"""
                                <destination>
                                    <international>
                                        <country-code>{country_code.replace(" ","")}</country-code>
                                    </international>
                                </destination>
                            </mailing-scenario>"""
            else:         
                xml_content += f""" 
                                <destination>
                                    <domestic>                      
                                        <postal-code>{postal_code.replace(" ","")}</postal-code>
                                    </domestic>
                                </destination>
                            </mailing-scenario>"""


            response = requests.post(url=url, data=xml_content, headers=headers)
            print(response.content)
            if response.status_code != 200:
                return Response({
                        "message": "Please enter valid data !!!",
                    }, status=status.HTTP_400_BAD_REQUEST)

            json_decoded = xmltodict.parse(response.content)
            print("json decoded", json_decoded)
            output_data = []
            for data in json_decoded["price-quotes"]["price-quote"]:
                output_data.append(
                    {
                        "price": data.get("price-details", {}).get("base"),
                        "taxes": "1.3",
                        "service_name": data.get("service-name"),
                        "service_code": data.get("service-code"),
                    }
                )
            if output_data:
                return Response(output_data, status=status.HTTP_200_OK)
            else:
                return Response(response, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )

        
class GetArtifactAPI(APIView):
    """
    Get lable for the shipment

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized or Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            get_link = request.data.get("artifact_link")
            if not get_link:
                return Response(
                    {"message": "artifact link not found!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            headers = {
                "Accept": "application/pdf",
                # "Content-Type": "application/vnd.cpc.shipment-v8+xml",
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            response = requests.get(url=get_link, headers=headers)
            with io.BytesIO(response.content) as pdf_stream:
                pdf_document = fitz.open(stream=pdf_stream)
                page = pdf_document[0]
                page_img = page.get_pixmap()
                base64_encoded = base64.b64encode(page_img.tobytes()).decode("utf-8")

            if response.status_code == 200:
                return HttpResponse(
                    base64_encoded,
                    status=status.HTTP_200_OK,
                    content_type="application/pdf",
                )
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )