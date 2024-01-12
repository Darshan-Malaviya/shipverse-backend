import requests
import os, io
import xmltodict
import base64
import fitz  # PyMuPDF
from rest_framework import status
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CandapostUserDetails, UserCarrier
from .common import add_carrier_user
from .serializers import UserCarrierSerializer
import shipverse.constant as const
from shipverse.models import *
from .utils import *
from .response import func_response
from .decorators import *

class CanadaUsersAccountDetails(APIView):
    """
    Step1 -  Create canada post account.

    """
    @authenticate_user
    def post(self, request):
            user = request.user
            serializer = UserCarrierSerializer(data=request.data)

            if not serializer.is_valid():
                return func_response("failed",serializer.errors)

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
                token_id = json_decoded.get("token",{}).get("token-id")


                if result.status_code == 200:
                    redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
                    _ = add_carrier_user(user, request.data, token_id=token_id)

                    data = {
                            "redirectUrl": redirect_url
                            + "?token-id="
                            + json_decoded.get("token", {}).get("token-id")
                            + "&platform-id="
                            + str(const.customerNo)
                            + f"&return-url={const.cpVerify_link}"
                        }
                    return func_response("success",data)
                else:
                    return func_response("failed",json_decoded.get("messages", {}).get("message"))
            else:
                add_carrier_user(user, request.data)
            return Response({}, status=status.HTTP_200_OK)


class VerifyCanadaPost(APIView):
    """
    Step2 - Verify the carrier account

    """
    @authenticate_user
    @validate_token
    def post(self, request):
        token_id = request.data.get("tokenId")
        user = request.user

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
            return func_response("success",json_decoded["merchant-info"])
        else:
            return func_response("failed",json_decoded["messages"]["message"])


class ShipmentCreateAPI(APIView):
    """
    Create shipment in Canada Post
    """

    @authenticate_user
    def post(self, request):
            user = request.user
            user_carrier = UserCarrier.objects.filter(user=user).first()
            from_location = FromLocation.objects.filter(userId = user.id).first()
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

            if not payment_option == "CreditCard":
                settlement_info = {
                    "contract_id": "0044084515",
                    "intended_method_of_payment": "CreditCard",
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
                return func_response("success",response)
            else:
                return func_response("failed",json_decoded)


class CanadaPostPrice(APIView):
    """
    Get price form the canada post

    """
    @authenticate_user
    def post(self, request):

        origin_postal_code = request.data.get("origin_postal_code")
        postal_code = request.data.get("postal_code")
        country_code = request.data.get("country_code")

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
        if country_code == "CA":
            xml_content += f""" 
                            <destination>
                                <domestic>                      
                                    <postal-code>{postal_code.replace(" ","")}</postal-code>
                                </domestic>
                            </destination>
                            """
            
        elif country_code == "US":
            xml_content += f"""
                            <destination>
                                <united-states>
                                    <zip-code>{postal_code.replace(" ","")}</zip-code>
                                </united-states>
                            </destination>
                            """
        else:         
            xml_content += f""" 
                            <destination>
                                <international>                      
                                    <country-code>{country_code.replace(" ","")}</country-code>
                                </international>
                            </destination>"""
        xml_content +=f"""</mailing-scenario>"""

        response = requests.post(url=url, data=xml_content, headers=headers)
        json_decoded = xmltodict.parse(response.content)
        if response.status_code != 200:
            return func_response("failed",json_decoded)
        output_data = []
        data_list = json_decoded["price-quotes"]["price-quote"]
        if type(json_decoded["price-quotes"]["price-quote"]) == dict:
            data_list = [json_decoded["price-quotes"]["price-quote"]]
        
        for data in data_list:
            output_data.append(
                {
                    "price": data.get("price-details", {}).get("base"),
                    "taxes": "1.3",
                    "service_name": data.get("service-name"),
                    "service_code": data.get("service-code"),
                }
            )
        if output_data:
            return func_response("success",output_data)
        else:
            return func_response("failed",response)

        
class GetArtifactAPI(APIView):
    """
    Get lable for the shipment

    """
    @authenticate_user
    def post(self, request):
        
        get_link = request.data.get("artifact_link")
        if not get_link:
            return func_response("failed","artifact link not found!")
        
        
        headers = {
            "Accept": "application/pdf",
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
