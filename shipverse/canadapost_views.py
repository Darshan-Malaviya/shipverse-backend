from rest_framework.views import APIView
from .auth import getUserIdByToken
from .models import Users, CandapostUserDetails, ShipperLocation, UserCarrier
from rest_framework.response import Response
import base64
import requests
from rest_framework import status
import xmltodict
from .common import add_carrier_user
import os
import json
from .serializers import UserCarrierSerializer, CanadaPostPriceSerializer
from shipverse import ServiceBase
import logging
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree

# from shipverse.util import InfoObject

class canada_users_account_details(APIView):
    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        print(auth_header)
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        if not user:
            return Response(
                {"message": "User not found or Unauthorized !"},
                status=status.HTTP_200_OK,
            )

        serializer = UserCarrierSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors)

        if request.data["carrier"]:
            # url = "https://soa-gw.canadapost.ca/ot/token"
            url = "https://ct.soa-gw.canadapost.ca/ot/token"
            cred = base64.b64encode(
                str(
                    os.environ.get("canadapost_username_debug")
                    + ":"
                    + os.environ.get("canadapost_password_debug")
                ).encode("ascii")
            )
            result = requests.post(
                url=url,
                data=None,
                headers={
                    "Accept": "application/vnd.cpc.registration-v2+xml",
                    "Content-Type": "application/vnd.cpc.registration-v2+xml",
                    "Authorization": "Basic " + cred.decode("ascii"),
                    "Accept-language": "en-CA",
                },
            )
            json_decoded = xmltodict.parse(result.content)
            token_id = json_decoded["token"]["token-id"]
            # redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/merchant"
            redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
            if result.status_code == 200:
                user_carrier = add_carrier_user(user, request.data)
                response = {
                    "isSuccess": True,
                    "message": None,
                    "data": {
                        "redirectUrl": redirect_url
                        + "?token-id="
                        + json_decoded["token"]["token-id"]
                        + "&platform-id="
                        + str(user_carrier.id)
                        + "&return-url=https://dev1.goshipverse.com/cpVerify"
                        #  "redirectUrl":redirect_url+"?token-id="+json_decoded["token"]["token-id"]+"&platform-id="+str(user_carrier.id)+"&return-url=https://0df8-2409-4080-9d00-645c-b733-bdba-28f7-a89e.ngrok-free.app/verifyCP"
                    },
                }
            else:
                response = {
                    "isSuccess": False,
                    "message": json_decoded["messages"]["message"],
                    "data": None,
                }
            return Response(response, status=status.HTTP_200_OK)
        else:
            add_carrier_user(user, request.data)
        return Response({}, status=status.HTTP_200_OK)


class VerifyCanadaPost(APIView):
    def post(self, request):
        token_id = request.data["tokenId"]
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)

        if not user:
            return Response(
                {"message": "User not found or Unauthorized !"},
                status=status.HTTP_200_OK,
            )
        url = "https://ct.soa-gw.canadapost.ca/ot/token/" + token_id
        # url = "https://soa-gw.canadapost.ca/ot/token/"+token_id
        cred = base64.b64encode(
            str(
                os.environ.get("canadapost_username_debug")
                + ":"
                + os.environ.get("canadapost_password_debug")
            ).encode("ascii")
        )
        result = requests.get(
            url=url,
            headers={
                "Accept": "application/vnd.cpc.registration-v2+xml",
                "Content-Type": "application/vnd.cpc.registration-v2+xml",
                "Authorization": "Basic " + cred.decode("ascii"),
                "Accept-language": "en-CA",
            },
        )
        json_decoded = xmltodict.parse(result.content)
        print("json_decoded -----> ",json_decoded)

        print(type(json_decoded))

        # mydict = json.loads(json_decoded)

        customer_number = json_decoded.get("merchant-info").get("customer-number")
        contract_number = json_decoded.get("merchant-info").get("contract-number")
        merchant_username = json_decoded.get("merchant-info").get("merchant-username")
        merchant_password = json_decoded.get("merchant-info").get("merchant-password")
        is_credit_card = json_decoded.get("merchant-info").get(
            "has-default-credit-card"
        )

        if result.status_code == 200:
            candapost_obj = CandapostUserDetails(
                user=user,
                customer_number=customer_number,
                contract_number=contract_number,
                merchant_username=merchant_username,
                merchant_password=merchant_password,
                has_credit_card=is_credit_card,
            )

            candapost_obj.save()
            print(candapost_obj)

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
    

class ShipmentCreateAPI(APIView):
    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        user_canadapost = CandapostUserDetails.objects.filter(user__id=user_id).first()
        if not user:
            return Response(
                {"message": "User not found or Unauthorized !"},
                status=status.HTTP_200_OK,
            )
    
        user_carrier = UserCarrier.objects.filter(user_id=user_id).first()

        data = request.data

        customer_no = user_canadapost.customer_number
        group_id = data.get("group_id")
        shipping_request_point = data.get("shipmentData",{}).get("zip")
        service_code = data.get("service_code") or "DOM.RP"   # Valid code representing the Canada Post delivery service used for shipping the item("Regular Parcel", "Xpresspost").
        
        # Sender's Info
        sender_name = user.username
        sender_company = user_carrier.company_name
        sender_phone_no = user_carrier.phone
        sender_address_line_1 = user_carrier.street1
        sender_city = user_carrier.city
        sender_state = user_carrier.state
        sender_country_code = user_carrier.country
        sender_postal_zip_code = user_carrier.postcode


        # Receiver's Info
        receiver_name = data.get("shipmentData", {}).get("recipient")
        receiver_company = data.get("soldTo", {}).get("companyName")
        receiver_address_line_1 = data.get("shipmentData", {}).get("street")
        receiver_city = data.get("shipmentData", {}).get("city")
        receiver_state = data.get("shipmentData", {}).get("stateCode")
        receiver_country_code = data.get("shipmentData", {}).get("countryCode")
        receiver_postal_zip_code = data.get("shipmentData", {}).get("zip")

        # Parcel Info
        parcel_weight = data.get("shipmentData", {}).get("weight")
        parcel_length = data.get("shipmentData", {}).get("length")
        parcel_width = data.get("shipmentData", {}).get("width")
        parcel_height = data.get("shipmentData", {}).get("height")

        # Send Notification to
        notification_email = user.email

        contract_id = user_canadapost.contract_number
        intended_method_of_payment = data.get("shipmentData",{}).get("paymentInformation",{}).get("paymentMethod")


        url = f"https://ct.soa-gw.canadapost.ca/rs/{customer_no}/{customer_no}/shipment"

        payload = f"""<shipment xmlns="http://www.canadapost.ca/ws/shipment-v8">
                            <group-id>{group_id}</group-id>
                            <requested-shipping-point>{shipping_request_point}</requested-shipping-point>
                            <delivery-spec>
                                <service-code>{service_code}</service-code>
                                <sender>
                                    <name>{sender_name}</name>
                                    <company>{sender_company}</company>
                                    <contact-phone>{sender_phone_no}</contact-phone>
                                    <address-details>
                                        <address-line-1>{sender_address_line_1}</address-line-1>
                                        <city>{sender_city}</city>
                                        <prov-state>{sender_state}</prov-state>
                                        <country-code>{sender_country_code}</country-code>
                                        <postal-zip-code>{sender_postal_zip_code}</postal-zip-code>
                                    </address-details>
                                </sender>
                                <destination>
                                    <name>{receiver_name}</name>
                                    <company>{receiver_company}</company>
                                    <address-details>
                                        <address-line-1>{receiver_address_line_1}</address-line-1>
                                        <city>{receiver_city}</city>
                                        <prov-state>{receiver_state}</prov-state>
                                        <country-code>{receiver_country_code}</country-code>
                                        <postal-zip-code>{receiver_postal_zip_code}</postal-zip-code>
                                    </address-details>
                                </destination>
                                <parcel-characteristics>
                                    <weight>{parcel_weight}</weight>
                                    <dimensions>
                                        <length>{parcel_length}</length>
                                        <width>{parcel_width}</width>
                                        <height>{parcel_height}</height>
                                    </dimensions>
                                    <mailing-tube>false</mailing-tube>
                                </parcel-characteristics>
                                <notification>
                                    <email>{notification_email}</email>
                                    <on-shipment>true</on-shipment>
                                    <on-exception>false</on-exception>
                                    <on-delivery>true</on-delivery>
                                </notification>
                                <print-preferences>
                                    <output-format>8.5x11</output-format>
                                </print-preferences>
                                <preferences>
                                    <show-packing-instructions>true</show-packing-instructions>
                                    <show-postage-rate>false</show-postage-rate>
                                    <show-insured-value>true</show-insured-value>
                                </preferences>
                                <settlement-info>
                                    <contract-id>{contract_id}</contract-id>
                                    <intended-method-of-payment>{intended_method_of_payment}</intended-method-of-payment>
                                </settlement-info>
                            </delivery-spec>
                        </shipment>"""
        
        cred = base64.b64encode(
            str(
                os.environ.get("canadapost_username_debug")
                + ":"
                + os.environ.get("canadapost_password_debug")
            ).encode("ascii")
        )

        headers = {
            "Accept": "application/vnd.cpc.ship.rate-v4+xml",
            "Content-Type": "application/vnd.cpc.ship.rate-v4+xml",
            "Authorization": "Basic " + cred.decode("ascii"),
            "Accept-language": "en-CA",
        }

        result = requests.request("POST", url, headers=headers, data=payload)
        json_decoded = xmltodict.parse(result.content)
        print("price-quotes ::", json_decoded)

        if result.status_code == 200:
            response = {
                "shipment-id": json_decoded.get("shipment-id"),
                "shipment-status": json_decoded.get("shipment-status"),
                "tracking-pin": json_decoded.get("tracking-pin")
            }

        else:
            response = {
                "shipment-id": None
            }

        return Response(response, status=status.HTTP_200_OK)   


class CanadaPostPrice(APIView):
    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        user_canadapost = CandapostUserDetails.objects.filter(user__id=user_id).first()
        serializers = CanadaPostPriceSerializer(data=request.data)
        if not serializers.is_valid():
            return Response(data=serializers.errors, status=status.HTTP_400_BAD_REQUEST)

        origin_postal_code = request.data.get("origin_postal_code")
        postal_code = request.data.get("postal_code")
        if not user:
            return Response(
                {"message": "User not found or Unauthorized !"},
                status=status.HTTP_200_OK,
            )

        url = "https://ct.soa-gw.canadapost.ca/rs/ship/price"
        cred = base64.b64encode(
            str(
                os.environ.get("canadapost_username_debug")
                + ":"
                + os.environ.get("canadapost_password_debug")
            ).encode("ascii")
        )
        headers = {
            "Accept": "application/vnd.cpc.ship.rate-v4+xml",
            "Content-Type": "application/vnd.cpc.ship.rate-v4+xml",
            "Authorization": "Basic " + cred.decode("ascii"),
            "Accept-language": "en-CA",
        }

        xml_content = f"""
            <mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
            <customer-number>{user_canadapost.customer_number}</customer-number>
            <parcel-characteristics>
            <weight>1</weight>
            </parcel-characteristics>
            <origin-postal-code>{origin_postal_code}</origin-postal-code>
            <destination>
            <domestic>
            <postal-code>{postal_code}</postal-code>
            </domestic>
            </destination>
            </mailing-scenario>
            """

        response = requests.post(url=url, data=xml_content, headers=headers)

        json_decoded = xmltodict.parse(response.content)
        price = json_decoded["price-quotes"]["price-quote"][0]["price-details"]["base"]

        return Response(data={"price": price}, status=status.HTTP_200_OK)
