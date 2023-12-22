import requests
import xmltodict
from rest_framework import status
from django.http import HttpResponse
from .auth import getUserIdByToken
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Users, CandapostUserDetails, UserCarrier
from .common import add_carrier_user
from .serializers import UserCarrierSerializer, CanadaPostPriceSerializer
import shipverse.constant as const


class CanadaUsersAccountDetails(APIView):
    """
    Step1 -  Create canada post account.

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            user_id = getUserIdByToken(auth_header)
            user = Users.objects.get(id=user_id)
            canadaPost_user = CandapostUserDetails.objects.filter(user=user).first()
            if not user:
                return Response(
                    {"message": "User not found or Unauthorized !"},
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

                if result.status_code == 200:
                    redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
                    user_carrier = add_carrier_user(user, request.data)
                    response = {
                        "isSuccess": True,
                        "message": None,
                        "data": {
                            "redirectUrl": redirect_url
                            + "?token-id="
                            + json_decoded.get("token", {}).get("token-id")
                            + "&platform-id="
                            + str(const.customerNo)  # TODO add customer number
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
            try:
                user_id = getUserIdByToken(auth_header)
            except:
                return Response(
                    {"message": "Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            try:
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized !"},
                    status=status.HTTP_200_OK,
                )
            token_id = request.data["tokenId"]
            if token_id:
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
                        {"message": "Token id required!"}, status=status.HTTP_200_OK
                )
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )


class ShipmentCreateAPI(APIView):
    """
    Create shipment in canada post

    """

    def post(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
            except:
                return Response(
                    {"message": "Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            try:
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized !"},
                    status=status.HTTP_200_OK,
                )
            user_canadapost = CandapostUserDetails.objects.filter(user__id=user_id).first()

            user_carrier = UserCarrier.objects.filter(user_id=user_id).first()

            data = request.data

            customer_no = user_canadapost.customer_number
            group_id = data.get("group_id")
            shipping_request_point = data.get("shipmentData", {}).get("zip")
            service_code = data.get("service_code") or "DOM.RP"

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
            intended_method_of_payment = (
                data.get("shipmentData", {})
                .get("paymentInformation", {})
                .get("paymentMethod")
            )

            url = f"https://{const.canadaPost}/rs/{customer_no}/{customer_no}/shipment"

            payload = f"""<shipment xmlns={const.xmlns}>
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

            headers = {
                "Accept": const.contentTypeShipRateXml,
                "Content-Type": const.contentTypeShipRateXml,
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            result = requests.request("POST", url, headers=headers, data=payload)
            json_decoded = xmltodict.parse(result.content)

            if result.status_code == 200:
                response = {
                    "shipment-id": json_decoded.get("shipment-id"),
                    "shipment-status": json_decoded.get("shipment-status"),
                    "tracking-pin": json_decoded.get("tracking-pin"),
                }

            else:
                response = {
                    "shipment-id": None,
                    "shipment-status": False,
                    "tracking-pin": None,
                }

            return Response(response, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )


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
                    {"message": "User not found or Unauthorized or please verify email !"},
                    status=status.HTTP_200_OK,
                )
            serializers = CanadaPostPriceSerializer(data=request.data)
            if not serializers.is_valid():
                return Response(data=serializers.errors, status=status.HTTP_400_BAD_REQUEST)

            origin_postal_code = request.data.get("origin_postal_code")
            postal_code = request.data.get("postal_code")
            if request.data.get("weight"):
                weight = request.data.get("weight")
                # length = request.data.get("length")
                # width = request.data.get("width")
                # height = request.data.get("height")

            else:
                weight = "1"
                # length = "33"
                # width = "25"
                # height = "33"

            url = f"https://{const.canadaPost}/rs/ship/price"
            headers = {
                "Accept": const.contentTypeShipRateXml,
                "Content-Type": const.contentTypeShipRateXml,
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            xml_content = f"""
                <mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
                <customer-number>0006006116</customer-number>
                <parcel-characteristics>
                <weight>{weight}</weight>

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
            output_data = []
            for data in json_decoded["price-quotes"]["price-quote"]:
                output_data.append(
                    {
                        "price": data.get("price-details", {}).get("base"),
                        "taxes": "1.3",
                        "service_name": data.get("service-name"),
                    }
                )
            if output_data:
                response = {
                    "message": "price details",
                    "data": output_data
                }
                return Response(response, status=status.HTTP_200_OK)
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

    def get(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header:
            try:
                user_id = getUserIdByToken(auth_header)
            except:
                return Response(
                    {"message": "Invalid Token!"},
                    status=status.HTTP_200_OK,
                )
            try:
                user = Users.objects.get(id=user_id, isEmailVerified = True)
            except:
                return Response(
                    {"message": "User not found or Unauthorized !"},
                    status=status.HTTP_200_OK,
                )
            get_link = request.data.get("artifact_link")
            if not get_link:
                return Response(
                    {"message": "artifact link not found!"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            headers = {
                "Accept": "application/pdf",
                "Content-Type": "application/vnd.cpc.shipment-v8+xml",
                "Authorization": "Basic " + const.encoded_cred,
                "Accept-language": const.acceptLanguage,
            }

            response = requests.get(url=get_link, headers=headers)
            if response.status_code == 200:
                return HttpResponse(
                    response.content,
                    status=status.HTTP_200_OK,
                    content_type="application/pdf",
                )
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": "Authorization token not found!"}, status=status.HTTP_200_OK
            )
