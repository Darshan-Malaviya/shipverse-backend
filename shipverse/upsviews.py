
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse
from shipverse.models import CarrierUsers, FromLocation, Shipment, ShipperLocation, Packages, Taxes, InternationalSettings, Users, UserCarrier
import requests
import base64
from django.db.models import Q
from rest_framework import status
import json
import uuid
from datetime import datetime
from shipverse.auth import decode_access_token, getUserIdByToken
import time
from django.conf import settings
from functools import wraps
import itertools
import jwt
from jwt.exceptions import ExpiredSignatureError

from shipverse.serializers import UPSSerializer
from django.core.serializers import serialize


@api_view(['POST'])
def isUPSAuth(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        carrieruser = CarrierUsers.objects.filter(
            userId=user_id)[0]
    except CarrierUsers.DoesNotExist:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    print('TTTTTTTTT', carrieruser)
    if not carrieruser.access_token or carrieruser.access_token.strip() == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return JsonResponse({'isAuthorized': True})


@api_view(['POST'])
def validate(request):
    user_data = JSONParser().parse(request)
    ups_redirect_uri = user_data['ups_redirect_uri']
    ups_validate_endpoint = user_data['ups_validate_endpoint']
    query = {
        "client_id": settings.UPS_CLIENT_ID,
        "redirect_uri": ups_redirect_uri
    }

    response = requests.get(ups_validate_endpoint, params=query)
    data = response.json()
    return JsonResponse(data)


@api_view(['POST'])
def getToken(request):
    user_data = JSONParser().parse(request)
    authcode = user_data['code']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    ups_redirect_uri = user_data['ups_redirect_uri']
    ups_token_endpoint = user_data['ups_token_endpoint']
    accountNumber = user_data['accountNumber']
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except CarrierUsers.DoesNotExist:
        carrieruser = CarrierUsers(userId=user_id, accountNumber=accountNumber)
        carrieruser.userId = user_id
        carrieruser.accountNumber = accountNumber

    payload = {
        "grant_type": "authorization_code",
        "code": authcode,
        "redirect_uri": ups_redirect_uri
    }
    # Encode the authorization credentials as base64
    auth_str = f"{settings.UPS_CLIENT_ID}:{settings.UPS_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_b64}"
    }
    response = requests.post(ups_token_endpoint, data=payload,
                             headers=headers)

    # response = requests.post(tokenendpoint, data=payload, headers=headers,
    #  auth=(client_id, client_secret))
    if (response):
        data = response.json()
        carrieruser.status = data['status']
        carrieruser.access_token = data['access_token']
        carrieruser.refresh_token = data['refresh_token']
        carrieruser.save()  # Save the new object to the database

        carrier_users = CarrierUsers.objects.filter(
            accountNumber=accountNumber)

        # Update the desired fields for each StoreUser object
        for carrier_user in carrier_users:
            carrier_user.access_token = data['access_token']
            carrier_user.refresh_token = data['refresh_token']
            carrier_user.save()
        return JsonResponse(data)
    return JsonResponse({"result": "failed"})


@api_view(['POST'])
def refreshToken(request):
    user_data = JSONParser().parse(request)
    accountNumber = user_data['accountNumber']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    ups_refreshtoken_endpoint = user_data['ups_refreshtoken_endpoint']
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except CarrierUsers.DoesNotExist:
        return JsonResponse({'CarrierUser not exists': False}, status=status.HTTP_401_UNAUTHORIZED)
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": carrieruser.refresh_token
    }
    # Encode the authorization credentials as base64
    auth_str = f"{settings.UPS_CLIENT_ID}:{settings.UPS_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_b64}"
    }
    response = requests.post(ups_refreshtoken_endpoint,
                             data=payload, headers=headers)
    print(headers)
    if (response):
        data = response.json()

        carrieruser.status = data['status']
        carrieruser.access_token = data['access_token']
        carrieruser.refresh_token = data['refresh_token']
        carrieruser.save()  # Save the new object to the database
        carrier_users = CarrierUsers.objects.filter(
            accountNumber=accountNumber)

        # Update the desired fields for each StoreUser object
        for carrier_user in carrier_users:
            carrier_user.access_token = data['access_token']
            carrier_user.refresh_token = data['refresh_token']
            carrier_user.save()
        return JsonResponse(data)
    return JsonResponse({'data': response.json()}, status=status.HTTP_200_OK)


@api_view(['POST'])
def disconnect(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    accountNumber = user_data['accountNumber']
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except:
        return JsonResponse({'CarrierUser not exists': False}, status=status.HTTP_401_UNAUTHORIZED)
    carrieruser.access_token = ""
    carrieruser.save()
    return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def addUser(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        shipperlocation = ShipperLocation.objects.get(
            userId=user_id, fullName=user_data['shipperLocation']['shipper_fullName'])
    except:
        shipperlocation = ShipperLocation(
            userId=user_id, fullName=user_data['shipperLocation']['shipper_fullName'])
    shipperlocation.userId = user_id
    shipperlocation.fullName = user_data['shipperLocation']['shipper_fullName']
    shipperlocation.attentionname = user_data['shipperLocation']['shipper_attentionname']
    shipperlocation.taxidnum = user_data['shipperLocation']['shipper_taxidnum']
    shipperlocation.phone = user_data['shipperLocation']['shipper_phone']
    shipperlocation.shipperno = user_data['shipperLocation']['shipper_number']
    shipperlocation.fax = user_data['shipperLocation']['shipper_fax']
    shipperlocation.address = user_data['shipperLocation']['shipper_address']
    shipperlocation.city = user_data['shipperLocation']['shipper_city']
    shipperlocation.statecode = user_data['shipperLocation']['shipper_statecode']
    shipperlocation.postalcode = user_data['shipperLocation']['shipper_postalcode']
    shipperlocation.countrycode = user_data['shipperLocation']['shipper_countrycode']
    shipperlocation.selected = True
    shipperlocation.save()
    # Set the selected flag of other shipperLocations to False
    other_shipper_locations = ShipperLocation.objects.filter(
        userId=user_id).exclude(id=shipperlocation.id)
    other_shipper_locations.update(selected=False)
    return JsonResponse({'saved': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getUsers(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    user = Users.objects.get(id=user_id)
    if not user :
        return JsonResponse({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
    registeredCarriers = UserCarrier.objects.filter(user=user)
    serialized = UPSSerializer(registeredCarriers,many=True)
    return JsonResponse({
        "isSuccess":True,
        "message":None,
        "data":serialized.data
    }, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def removeUser(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    user = Users.objects.get(id=user_id)
    if not user : 
        return JsonResponse({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
    shipperno = user_data['shipperno']
    try:
        shipperLocation = UserCarrier.objects.get(
            user=user, account_number=shipperno)   # Updated accountNumber to account_number
    except:
        return JsonResponse({'success': False}, status=status.HTTP_404_NOT_FOUND)
    shipperLocation.delete()
    return JsonResponse({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def addPackage(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        package = Packages.objects.get(
            userId=user_id, packageName=user_data['packageData']['packageName'])
    except:
        package = Packages(
            userId=user_id, packageName=user_data['packageData']['packageName'])

    package.packageName = user_data['packageData']['packageName']
    package.measureUnit = user_data['packageData']['measureUnit']
    package.length = user_data['packageData']['length']
    package.width = user_data['packageData']['width']
    package.height = user_data['packageData']['height']
    package.packageCode = "02"
    package.upsPackage = False
    package.save()
    return JsonResponse({'saved': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def updatePackage(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        package = Packages.objects.get(
            userId=user_id, packageName=user_data['packageData']['packageName'])
    except:
        package = Packages(
            userId=user_id, packageName=user_data['packageData']['packageName'])

    package.packageName = user_data['packageData']['packageName']
    package.measureUnit = user_data['packageData']['measureUnit']
    package.length = user_data['packageData']['length']
    package.width = user_data['packageData']['width']
    package.height = user_data['packageData']['height']
    package.packageCode = "02"
    package.upsPackage = False
    package.save()
    return JsonResponse({'saved': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getPackages(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    packages = Packages.objects.filter(
        Q(userId=user_id) | Q(userId=0)).order_by('id')

    packages_dict = []
    for package in packages:
        package_dict = {
            'id': package.id,
            'userId': package.userId,
            'packageName': package.packageName,
            'measureUnit': package.measureUnit,
            'length': package.length,
            'width': package.width,
            'height': package.height,
            'packageCode': package.packageCode,
            'upsPackage': package.upsPackage,
            # Add more fields as needed
        }
        packages_dict.append(package_dict)
    # Create a JSON object containing the list of dictionaries
    json_data = json.dumps({'packages': packages_dict})
    return JsonResponse(json_data, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def removePackage(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    packageName = user_data['packageName']
    try:
        package = Packages.objects.get(
            userId=user_id, packageName=packageName)
    except:
        return JsonResponse({'success': False}, status=status.HTTP_404_NOT_FOUND)
    package.delete()
    return JsonResponse({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def makeDefaultUser(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    fullName = user_data['fullName']
    try:
        shipperLocation = ShipperLocation.objects.get(
            userId=user_id, fullName=fullName)
    except:
        return JsonResponse({'success': False}, status=status.HTTP_404_NOT_FOUND)
    shipperLocation.selected = True
    shipperLocation.save()
    # Set the selected flag of other shipperLocations to False
    other_shipper_locations = ShipperLocation.objects.filter(
        userId=user_id).exclude(id=shipperLocation.id)
    other_shipper_locations.update(selected=False)
    return JsonResponse({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def addFromLocation(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        fromlocation = FromLocation.objects.get(userId=user_id,
                                                locationName=user_data['fromLocation']['locationName'])
    except:
        fromlocation = FromLocation(userId=user_id,
                                    locationName=user_data['fromLocation']['locationName'])
    fromlocation.userId = user_id
    fromlocation.locationName = user_data['fromLocation']['locationName']
    fromlocation.fullName = user_data['fromLocation']['fullName']
    fromlocation.attentionName = user_data['fromLocation']['attentionName']
    fromlocation.phone = user_data['fromLocation']['phone']
    fromlocation.address = user_data['fromLocation']['address']
    fromlocation.address1 = user_data['fromLocation']['address1']
    fromlocation.city = user_data['fromLocation']['city']
    fromlocation.stateCode = user_data['fromLocation']['stateCode']
    fromlocation.postalCode = user_data['fromLocation']['postalCode']
    fromlocation.countryCode = user_data['fromLocation']['countryCode']
    fromlocation.email = user_data['fromLocation']['email']
    fromlocation.timezone = user_data['fromLocation']['timezone']
    fromlocation.residential = user_data['fromLocation']['residential']
    fromlocation.returnFullName = user_data['fromLocation']['returnFullName']
    fromlocation.returnAttentionName = user_data['fromLocation']['returnAttentionName']
    fromlocation.returnPhone = user_data['fromLocation']['returnPhone']
    fromlocation.returnAddress = user_data['fromLocation']['returnAddress']
    fromlocation.returnAddress1 = user_data['fromLocation']['returnAddress1']
    fromlocation.returnCity = user_data['fromLocation']['returnCity']
    fromlocation.returnStateCode = user_data['fromLocation']['returnStateCode']
    fromlocation.returnPostalCode = user_data['fromLocation']['returnPostalCode']
    fromlocation.returnCountryCode = user_data['fromLocation']['returnCountryCode']
    fromlocation.returnEmail = user_data['fromLocation']['returnEmail']
    fromlocation.returnTimezone = user_data['fromLocation']['returnTimezone']
    fromlocation.save()
    return JsonResponse({'result': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def updateFromLocation(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        fromlocation = FromLocation.objects.get(userId=user_id, locationName=user_data['fromLocation']['locationName'])
    except:
        fromlocation = FromLocation(userId=user_id, locationName=user_data['fromLocation']['locationName'])
        
    required_list = ['locationName','fullName','attentionName','phone','address','address1','city','stateCode','postalCode','countryCode','email','timezone','selected','residential','returnFullName','returnAttentionName','returnPhone','returnAddress','returnAddress1','returnCity','returnStateCode','returnPostalCode','returnCountryCode','returnEmail','returnTimezone']
    
    for req in required_list:
        if user_data['fromLocation'][req] == "":
            return JsonResponse({'result': False,'message' : "The location feild should not be Empty !"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    fromlocation.userId = user_id
    fromlocation.locationName = user_data['fromLocation']['locationName']
    fromlocation.fullName = user_data['fromLocation']['fullName']
    fromlocation.attentionName = user_data['fromLocation']['attentionName']
    fromlocation.phone = user_data['fromLocation']['phone']
    fromlocation.address = user_data['fromLocation']['address']
    fromlocation.address1 = user_data['fromLocation']['address1']
    fromlocation.city = user_data['fromLocation']['city']
    fromlocation.stateCode = user_data['fromLocation']['stateCode']
    fromlocation.postalCode = user_data['fromLocation']['postalCode']
    fromlocation.countryCode = user_data['fromLocation']['countryCode']
    fromlocation.email = user_data['fromLocation']['email']
    fromlocation.timezone = user_data['fromLocation']['timezone']
    fromlocation.selected = user_data['fromLocation']['selected']
    fromlocation.residential = user_data['fromLocation']['residential']
    fromlocation.returnFullName = user_data['fromLocation']['returnFullName']
    fromlocation.returnAttentionName = user_data['fromLocation']['returnAttentionName']
    fromlocation.returnPhone = user_data['fromLocation']['returnPhone']
    fromlocation.returnAddress = user_data['fromLocation']['returnAddress']
    fromlocation.returnAddress1 = user_data['fromLocation']['returnAddress1']
    fromlocation.returnCity = user_data['fromLocation']['returnCity']
    fromlocation.returnStateCode = user_data['fromLocation']['returnStateCode']
    fromlocation.returnPostalCode = user_data['fromLocation']['returnPostalCode']
    fromlocation.returnCountryCode = user_data['fromLocation']['returnCountryCode']
    fromlocation.returnEmail = user_data['fromLocation']['returnEmail']
    fromlocation.returnTimezone = user_data['fromLocation']['returnTimezone']
    fromlocation.save()
    return JsonResponse({'result': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def deleteFromLocation(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    id = user_data['id']
    try:
        fromlocation = FromLocation.objects.get(
            userId=user_id, id=id)
    except:
        return JsonResponse({'success': False}, status=status.HTTP_404_NOT_FOUND)
    fromlocation.delete()
    return JsonResponse({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getFromLocations(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    fromLocations = FromLocation.objects.filter(
        userId=user_id).order_by('selected')
    Packages.objects.filter(
        Q(userId=user_id) | Q(userId=0)).order_by('packageCode')
    fromLocations_dict_list = []
    for fromLocation in fromLocations:
        fromLocation_dict = {
            'id': fromLocation.id,
            'userId': fromLocation.userId,
            'locationName': fromLocation.locationName,
            'fullName': fromLocation.fullName,
            'attentionName': fromLocation.attentionName,
            'phone': fromLocation.phone,
            'address': fromLocation.address,
            'address1': fromLocation.address1,
            'city': fromLocation.city,
            'stateCode': fromLocation.stateCode,
            'postalCode': fromLocation.postalCode,
            'countryCode': fromLocation.countryCode,
            'selected': fromLocation.selected,
            'residential': fromLocation.residential,
            'email': fromLocation.email,
            'timezone': fromLocation.timezone,
            'returnFullName': fromLocation.returnFullName,
            'returnAttentionName': fromLocation.returnAttentionName,
            'returnPhone': fromLocation.returnPhone,
            'returnAddress': fromLocation.returnAddress,
            'returnAddress1': fromLocation.returnAddress1,
            'returnCity': fromLocation.returnCity,
            'returnStateCode': fromLocation.returnStateCode,
            'returnPostalCode': fromLocation.returnPostalCode,
            'returnCountryCode': fromLocation.returnCountryCode,
            'returnEmail': fromLocation.returnEmail,
            'returnTimezone': fromLocation.returnTimezone,
            # Add more fields as needed
        }
        fromLocations_dict_list.append(fromLocation_dict)
    # Create a JSON object containing the list of dictionaries
    json_data = json.dumps({'fromLocations': fromLocations_dict_list})
    return JsonResponse(json_data, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def checkAddressValidation(request):
    user_data = JSONParser().parse(request)
    accountNumber = user_data['accountNumber']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except CarrierUsers.DoesNotExist:
        return JsonResponse({"status": "CarrierUser doesn't exist"}, status=status.HTTP_401_UNAUTHORIZED, safe=False)
    version = "v1"
    ups_addressValidation_endpoint = user_data['ups_addressValidation_endpoint']
    url = ups_addressValidation_endpoint + version + "/1"
    headers = {
        "Content-Type": "application/json",
        "transId": str(uuid.uuid4()),
        "transactionSrc": "testing",
        "Authorization": "Bearer "+carrieruser.access_token
    }
    query = {
        "regionalrequestindicator": "TRUE",
        "maximumcandidatelistsize": "15"
    }

    payload = {
        "XAVRequest": {
            "AddressKeyFormat": {
                "ConsigneeName": user_data.get('recipient'),
                "BuildingName": "",
                "AddressLine": [
                    user_data.get('street'),
                ],
                # "Region": "ROSWELL,GA,30076-1521",
                "PoliticalDivision2": user_data.get('city'),
                "PoliticalDivision1": user_data.get('stateCode'),
                "PostcodePrimaryLow": user_data.get('zip'),
                # "PostcodeExtendedLow": "",
                # "Urbanization": "porto arundal",
                "CountryCode": user_data.get('countryCode')
            }
        }
    }
    response = requests.post(
        url, json=payload, headers=headers, params=query)
    data = response.json()
    if 'response' in data and 'errors' in data['response'] and data['response']['errors']:
        return JsonResponse({"result": "Failed", "data": data['response']['errors'][0]['message']}, status=status.HTTP_401_UNAUTHORIZED)
    return JsonResponse({"result": "Success", "data": data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getLabel(request):
    user_data = JSONParser().parse(request)
    accountNumber = user_data['accountNumber']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    order = user_data['order']
    try:
        shipment = Shipment.objects.get(
            userId=user_id, order=order)
    except:
        return JsonResponse({"status": "order doesn't exist"}, status=status.HTTP_404_NOT_FOUND, safe=False)

    return JsonResponse({"image": shipment.image}, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def getInvoice(request):
    user_data = JSONParser().parse(request)
    accountNumber = user_data['accountNumber']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    order = user_data['order']
    try:
        shipment = Shipment.objects.get(
            userId=user_id, order=order)
    except:
        return JsonResponse({"status": "order doesn't exist"}, status=status.HTTP_404_NOT_FOUND, safe=False)

    return JsonResponse({"invoice": shipment.invoice}, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def getOrderRate(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    user_id = getUserIdByToken(auth_header)

    ups_rate_endpoint = user_data['ups_rate_endpoint']
    shipmentData = user_data.get('shipmentData')
    shipfromlocation = shipmentData['shipfrom_location']
    accountNumber = user_data.get('accountNumber')
    try:
        fromlocation = FromLocation.objects.get(
            userId=user_id, locationName=shipfromlocation)
    except:
        return JsonResponse({'FromLocation not exists': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        shipperlocation = ShipperLocation.objects.get(
            userId=user_id, shipperno=accountNumber)
    except:
        return JsonResponse({'ShipperLocation not exists': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except:
        return JsonResponse({'CarrierUser not exists': False},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    version = "v2201"
    requestoption = "Ratetimeintransit"

    url = ups_rate_endpoint + version + "/"+requestoption
    # "CONFIRMED_ADDRESS": UPS will verify the address against a database of known addresses and attempt to correct any errors.

    # "UNCONFIRMED_ADDRESS": UPS will attempt to validate the address based on the information provided, but will not attempt to correct any errors.

    # "NO_ADDRESS_VALIDATION": UPS will not perform any additional address validation beyond the standard validation that is performed for all shipments.
    query = {
        "additionalinfo": ""
    }
    payload = {
        "RateRequest": {
            "Request": {
                "SubVersion": "2205",
                "TransactionReference": {
                    "CustomerContext": "CustomerContext",
                    "TransactionIdentifier": "TransactionIdentifier"
                }
            },
            "Shipment": {
                # "Description": "",
                "Shipper": {
                    "Name": shipperlocation.fullName,
                    "ShipperNumber": shipperlocation.shipperno,
                    "Address": {
                        "AddressLine": shipperlocation.address,
                        "City": shipperlocation.city,
                        "StateProvinceCode": shipperlocation.statecode,
                        "PostalCode": shipperlocation.postalcode,
                        "CountryCode": shipperlocation.countrycode
                    }
                },
                "ShipTo": {
                    "Name": shipmentData['recipient'],
                    "Address": {
                        "AddressLine": shipmentData['street'],
                        "City": shipmentData['city'],
                        "StateProvinceCode": shipmentData['stateCode'],
                        "PostalCode": shipmentData['zip'],
                        "CountryCode": shipmentData['country_iso2']
                    },
                },
                "TaxInformationIndicator": "1",
                "ShipFrom": {
                    "Name": fromlocation.fullName,
                    "Address": {
                        "AddressLine": fromlocation.address,
                        "City": fromlocation.city,
                        "StateProvinceCode": fromlocation.stateCode,
                        "PostalCode": fromlocation.postalCode,
                        "CountryCode": fromlocation.countryCode
                    }
                },
                "ShipmentRatingOptions": {
                    "NegotiatedRatesIndicator": "2",
                    "UserLevelDiscountIndicator": "1"
                },

                "PaymentDetails": {
                    "ShipmentCharge": {
                        "Type": "01",
                        "BillShipper": {
                            "AccountNumber": shipperlocation.shipperno
                        }
                    }
                },
                "Service": {
                    "Code": shipmentData['service_code'],
                    "Description": ""
                },
                "Package": {
                    "PackagingType": {
                        "Code": shipmentData['package_code'],
                        "Description": "Packaging"
                    },
                    "Dimensions": {
                        "UnitOfMeasurement": {
                            "Code": "IN" if shipmentData['weight_code'] == "LBS" else "CM",
                            "Description": "Inches" if shipmentData['weight_code'] == "LBS" else ""
                        },
                        "Length": str(shipmentData['length']),
                        "Width": str(shipmentData['width']),
                        "Height": str(shipmentData['height'])
                    },
                    "PackageWeight": {
                        "UnitOfMeasurement": {
                            "Code": shipmentData['weight_code'],
                            "Description": "Pounds" if shipmentData['weight_code'] == "LBS" else ""
                        },
                        "Weight": shipmentData['weight']
                    },
                    "PackageServiceOptions": {
                        "DeclaredValue": {
                            "CurrencyCode": shipmentData['internationalForm']['curCode'],
                            "MonetaryValue": str(shipmentData['declared_value']) if str(shipmentData['declared_value']) != "" else "0"
                        }
                    }
                },
                "ShipmentTotalWeight": {
                    "UnitOfMeasurement": {
                        "Code": shipmentData['weight_code'],
                        "Description": "Pounds" if shipmentData['weight_code'] == "LBS" else ""
                    },
                    "Weight": shipmentData['weight']
                },
                "InvoiceLineTotal": {
                    "CurrencyCode": shipmentData['internationalForm']['curCode'],
                    "MonetaryValue": "50"
                },
                "DeliveryTimeInformation": {
                    "PackageBillType": "03",
                }
            }
        }
    }
    print(payload)
    headers = {
        "Content-Type": "application/json",
        "transId": str(uuid.uuid4()),
        "transactionSrc": "testing",
        "Authorization": "Bearer "+carrieruser.access_token
    }
    response = requests.post(
        url, json=payload, headers=headers, params=query)
    data = response.json()
    return JsonResponse({"result": "success", "data": data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getRateServices(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    user_id = getUserIdByToken(auth_header)

    ups_rate_endpoint = user_data['ups_rate_endpoint']
    shipmentData = user_data.get('shipmentData')
    shipfromlocation = shipmentData['shipfrom_location']
    accountNumber = user_data.get('accountNumber')
    try:
        fromlocation = FromLocation.objects.get(
            userId=user_id, locationName=shipfromlocation)
    except:
        return JsonResponse({'result': 'failed', 'data': 'FromLocation not exists'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        shipperlocation = ShipperLocation.objects.get(
            userId=user_id, shipperno=accountNumber)
    except:
        return JsonResponse({'result': 'failed', 'data': 'ShipperLocation not exists'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except:
        return JsonResponse({'result': 'failed', 'data': 'CarrierUser not exists'},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    version = "v1"
    requestoption = "Shop"

    url = ups_rate_endpoint + version + "/"+requestoption
    # "CONFIRMED_ADDRESS": UPS will verify the address against a database of known addresses and attempt to correct any errors.

    # "UNCONFIRMED_ADDRESS": UPS will attempt to validate the address based on the information provided, but will not attempt to correct any errors.

    # "NO_ADDRESS_VALIDATION": UPS will not perform any additional address validation beyond the standard validation that is performed for all shipments.
    query = {
        "additionalinfo": ""
    }
    payload = {
        "RateRequest": {
            "Request": {
                "TransactionReference": {
                    "CustomerContext": "CustomerContext",
                    "TransactionIdentifier": "TransactionIdentifier"
                }
            },
            "Shipment": {
                "Shipper": {
                    "Name": shipperlocation.fullName,
                    "ShipperNumber": shipperlocation.shipperno,
                    "Address": {
                        "AddressLine": shipperlocation.address,
                        "City": shipperlocation.city,
                        "StateProvinceCode": shipperlocation.statecode,
                        "PostalCode": shipperlocation.postalcode,
                        "CountryCode": shipperlocation.countrycode
                    }
                },
                "ShipTo": {
                    "Name": shipmentData['recipient'],
                    "Address": {
                        "AddressLine": shipmentData['street'],
                        "City": shipmentData['city'],
                        "StateProvinceCode": shipmentData['stateCode'],
                        "PostalCode": shipmentData['zip'],
                        "CountryCode": shipmentData['country_iso2']
                    },
                },
                "ShipFrom": {
                    "Name": fromlocation.fullName,
                    "Address": {
                        "AddressLine": fromlocation.address,
                        "City": fromlocation.city,
                        "StateProvinceCode": fromlocation.stateCode,
                        "PostalCode": fromlocation.postalCode,
                        "CountryCode": fromlocation.countryCode
                    }
                },
                "Package": {
                    "PackagingType": {
                        "Code": shipmentData['package_code'],
                        "Description": "Packaging"
                    },

                    "PackageWeight": {
                        "UnitOfMeasurement": {
                            "Code": shipmentData['weight_code'],
                            "Description": "Pounds" if shipmentData['weight_code'] == "LBS" else ""
                        },
                        "Weight": "1"
                    }
                },
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "transId": str(uuid.uuid4()),
        "transactionSrc": "testing",
        "Authorization": "Bearer "+carrieruser.access_token
    }
    response = requests.post(
        url, json=payload, headers=headers, params=query)
    data = response.json()
    return JsonResponse({"result": "success", "data": data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getOrderRates(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    user_id = getUserIdByToken(auth_header)

    ups_rate_endpoint = user_data['ups_rate_endpoint']
    shipmentData = user_data.get('shipmentData')
    shipfromlocation = shipmentData['shipfrom_location']
    accountNumber = user_data.get('accountNumber')
    serviceCodes = user_data.get('serviceCodes')
    weight = user_data.get('weight')
    try:
        fromlocation = FromLocation.objects.get(
            userId=user_id, locationName=shipfromlocation)
    except:
        return JsonResponse({'FromLocation not exists': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        shipperlocation = ShipperLocation.objects.get(
            userId=user_id, shipperno=accountNumber)
    except:
        return JsonResponse({'ShipperLocation not exists': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except:
        return JsonResponse({'CarrierUser not exists': False},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    version = "v1"
    requestoption = "Rate"

    url = ups_rate_endpoint + version + "/"+requestoption
    # "CONFIRMED_ADDRESS": UPS will verify the address against a database of known addresses and attempt to correct any errors.

    # "UNCONFIRMED_ADDRESS": UPS will attempt to validate the address based on the information provided, but will not attempt to correct any errors.

    # "NO_ADDRESS_VALIDATION": UPS will not perform any additional address validation beyond the standard validation that is performed for all shipments.
    query = {
        "additionalinfo": ""
    }
    headers = {
        "Content-Type": "application/json",
        "transId": str(uuid.uuid4()),
        "transactionSrc": "testing",
        "Authorization": "Bearer "+carrieruser.access_token
    }
    rates_dict_list = []
    for serviceCode in serviceCodes:
        payload = {
            "RateRequest": {
                "Request": {
                    "TransactionReference": {
                        "CustomerContext": "CustomerContext",
                        "TransactionIdentifier": "TransactionIdentifier"
                    }
                },
                "Shipment": {
                    "Shipper": {
                        "Name": shipperlocation.fullName,
                        "ShipperNumber": shipperlocation.shipperno,
                        "Address": {
                            "AddressLine": shipperlocation.address,
                            "City": shipperlocation.city,
                            "StateProvinceCode": shipperlocation.statecode,
                            "PostalCode": shipperlocation.postalcode,
                            "CountryCode": shipperlocation.countrycode
                        }
                    },
                    "ShipTo": {
                        "Name": shipmentData['recipient'],
                        "Address": {
                            "AddressLine": shipmentData['street'],
                            "City": shipmentData['city'],
                            "StateProvinceCode": shipmentData['state'],
                            "PostalCode": shipmentData['zip'],
                            "CountryCode": shipmentData['country_iso2']
                        },
                    },
                    "ShipFrom": {
                        "Name": fromlocation.fullName,
                        "Address": {
                            "AddressLine": fromlocation.address,
                            "City": fromlocation.city,
                            "StateProvinceCode": fromlocation.stateCode,
                            "PostalCode": fromlocation.postalCode,
                            "CountryCode": fromlocation.countryCode
                        }
                    },
                    "PaymentDetails": {
                        "ShipmentCharge": {
                            "Type": "01",
                            "BillShipper": {
                                "AccountNumber": shipperlocation.shipperno
                            }
                        }
                    },
                    "Service": {
                        "Code": serviceCode,
                        "Description": ""
                    },
                    "Package": {
                        "PackagingType": {
                            "Code": shipmentData['package_code'],
                            "Description": "Packaging"
                        },
                        "Dimensions": {
                            "UnitOfMeasurement": {
                                "Code": "IN" if shipmentData['weight_code'] == "LBS" else "CM",
                                "Description": "Inches"
                            },
                            "Length": shipmentData['length'],
                            "Width": shipmentData['width'],
                            "Height": shipmentData['height']
                        },
                        "PackageWeight": {
                            "UnitOfMeasurement": {
                                "Code": 'LBS',
                                "Description": "Pounds" if shipmentData['weight_code'] == "LBS" else ""
                            },
                            "Weight": str(weight)
                        },
                        "PackageServiceOptions": {
                            "DeclaredValue": {
                                "CurrencyCode": shipmentData['internationalForm']['curCode'],
                                "MonetaryValue": str(shipmentData['declared_value']) if str(shipmentData['declared_value']) != "" else "0"
                            }
                        }
                    },
                }
            }
        }
        try:
            response = requests.post(
                url, json=payload, headers=headers, params=query)
            data = response.json()
        except:
            return JsonResponse({"result": "failed", "data": data},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'errors' in data.get('response', {}):
            # Handle the case when there are errors in the response
            # ...
            return JsonResponse({"result": "failed", "data": data['response']['errors'][0]['message']},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            monetary_value = data['RateResponse']['RatedShipment']['TotalCharges']['MonetaryValue']
            currency_code = data['RateResponse']['RatedShipment']['TotalCharges']['CurrencyCode']

            if currency_code == 'CAD':
                # Use the monetary value when the currency code is CAD
                rate_dict_list = {
                    'serviceName': serviceCode,
                    'value': monetary_value,
                    'currency_code': currency_code
                }
                rates_dict_list.append(rate_dict_list)
    return JsonResponse({"result": "success", "data": rates_dict_list}, status=status.HTTP_200_OK)


@api_view(['POST'])
def createLabel(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    user_id = getUserIdByToken(auth_header)

    ups_shipment_endpoint = user_data['ups_shipment_endpoint']
    shipmentData = user_data.get('shipmentData')
    shipfromlocation = shipmentData['shipfrom_location']
    accountNumber = user_data.get('accountNumber')
    order = user_data.get('order')
    try:
        fromlocation = FromLocation.objects.get(
            userId=user_id, locationName=shipfromlocation)
    except:
        return JsonResponse({'result': "failed", 'data': 'FromLocation does not exists'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        shipperlocation = ShipperLocation.objects.get(
            userId=user_id, shipperno=accountNumber)
    except:
        return JsonResponse({'result': "failed", 'data': 'ShipperLocation does not exists'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        carrieruser = CarrierUsers.objects.get(
            userId=user_id, accountNumber=accountNumber)
    except:
        return JsonResponse({'CarrierUser not exists': False},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    version = "v1"
    url = ups_shipment_endpoint + version + "/ship"
    # "CONFIRMED_ADDRESS": UPS will verify the address against a database of known addresses and attempt to correct any errors.

    # "UNCONFIRMED_ADDRESS": UPS will attempt to validate the address based on the information provided, but will not attempt to correct any errors.

    # "NO_ADDRESS_VALIDATION": UPS will not perform any additional address validation beyond the standard validation that is performed for all shipments.
    query = {
        "additionaladdressvalidation": "NO_ADDRESS_VALIDATION"
    }
    products_dict = []
    products = shipmentData['products']
    totalValue = 0
    if shipmentData['customData']['taxId']:
        split_text = shipmentData['customData']['taxId'].split("-")
        shipmentData['customData']['taxId'] = split_text[0]
    else:
        shipmentData['customData']['taxId'] = ""
    for product in products:
        totalValue += float(product['quantity']) * float(product['value'])
        product_dict = {
            "Description": product['description'],
            "OriginCountryCode": product['countryCode'],
            "CommodityCode": product['harmonisation'],
            "Unit":
            {
                "Number": "1",
                "Value": product['value'],
                "UnitOfMeasurement":
                {
                    "Code": 'BOX',
                    "Description": 'BOX'
                },
            }
        }
        products_dict.append(product_dict)
    serviceOptions = {
        "InternationalForms": {
            "FormType": '01',
            "InvoiceNumber": shipmentData['internationalForm']['invoiceNumber'],
            "PurchaseOrderNumber": shipmentData['internationalForm']['purchaseOrder'],
            "TermsOfShipment": shipmentData['internationalForm']['termsOfSale'],
            "InvoiceDate": datetime.now().strftime('%Y%m%d'),
            "ReasonForExport": shipmentData['internationalForm']['reasonForExport'],
            "DeclarationStatement": shipmentData['internationalForm']['declarationStatement'],
            "Comments": shipmentData['internationalForm']['additionalComment'],
            "CurrencyCode": shipmentData['internationalForm']['curCode'],
            "Product": products_dict,
            "Contacts": {
                "SoldTo": {
                    "Name": shipmentData['recipient'],
                    "AttentionName": shipmentData['attention'],
                    "TaxIdentificationNumber": shipmentData['taxId'],
                    "Phone": {
                        "Number": shipmentData['phone']
                    },
                    "Address": {
                        "AddressLine": shipmentData['street'],
                        "City": shipmentData['city'],
                        "StateProvinceCode": shipmentData['state'],
                        "PostalCode": shipmentData['zip'],
                        "CountryCode": shipmentData['country_iso2']
                    },
                }
            },
        },
        "LabelDelivery": {
            "LabelLinksIndicator": "1"
        }
    }
    if shipmentData['isSoldTo'] == False:
        serviceOptions['InternationalForms']['Contacts']['SoldTo'] = {
            "Name": shipmentData['soldTo']['companyName'],
            "AttentionName": shipmentData['soldTo']['attentionName'],
            "TaxIdentificationNumber": shipmentData['soldTo']['taxId'],
            "Phone": {
                "Number": shipmentData['soldTo']['phone']
            },
            "Address": {
                "AddressLine": shipmentData['soldTo']['street'],
                "City": shipmentData['soldTo']['city'],
                "StateProvinceCode": shipmentData['soldTo']['stateCode'],
                "PostalCode": shipmentData['soldTo']['postalCode'],
                "CountryCode": shipmentData['soldTo']['countryCode']
            },
            "EMailAddress": shipmentData['soldTo']['email']
        }
    if (shipmentData['internationalForm']['discount'] != ""):
        serviceOptions["InternationalForms"]["Discount"] = {
            "MonetaryValue": shipmentData['internationalForm']['discount']}
    if (shipmentData['internationalForm']['freightCharge'] != ""):
        serviceOptions["InternationalForms"]["FreightCharges"] = {
            "MonetaryValue": shipmentData['internationalForm']['freightCharge']}
    if (shipmentData['internationalForm']['insurance'] != ""):
        serviceOptions["InternationalForms"]["InsuranceCharges"] = {
            "MonetaryValue": shipmentData['internationalForm']['insurance']}
    if (shipmentData['internationalForm']['otherCharge'] != ""):
        serviceOptions["InternationalForms"]["OtherCharges"] = {
            "MonetaryValue": shipmentData['internationalForm']['otherCharge'],
            "Description": shipmentData['internationalForm']['specify'], }
    if (shipmentData['paymentInformation']['paymentMethod']) == "01":
        paymentChargeInformation = {
            "Type": "01",
            "BillShipper": {
                    "AccountNumber": shipperlocation.shipperno
            }
        }
    elif (shipmentData['paymentInformation']['paymentMethod']) == "02":
        paymentChargeInformation = {
            "Type": "01",
            "BillReceiver": {
                "AccountNumber": shipmentData['paymentInformation']['accountNumber'],
                "Address": {
                    "PostalCode": shipmentData['paymentInformation']['postalCode']
                }
            }
        }
    elif (shipmentData['paymentInformation']['paymentMethod']) == "03":
        paymentChargeInformation = {
            "Type": "01",
            "BillThirdParty	": {
                "AccountNumber": shipmentData['paymentInformation']['accountNumber'],
                "Address": {
                    "PostalCode": shipmentData['paymentInformation']['postalCode'],
                    "CountryCode": shipmentData['paymentInformation']['countryCode']
                }
            }
        }
    elif (shipmentData['paymentInformation']['paymentMethod']) == "05":
        paymentChargeInformation = {
            "Type": "01",
            "BillShipper": {
                    "AlternatePaymentMethod": "01"  # PayPal
            }
        }

    # Duties And Taxes
    if shipmentData['dutiesAndTaxesInformation']['paymentMethod'] == "01":
        dutiesInformation = {
            "Type": "02",
            "ConsigneeBilledIndicator": "1"
        }
    elif shipmentData['dutiesAndTaxesInformation']['paymentMethod'] == "02":
        dutiesInformation = {
            "Type": "02",
            "BillShipper": {
                    "AccountNumber": shipperlocation.shipperno
            }
        }
    elif (shipmentData['dutiesAndTaxesInformation']['paymentMethod']) == "03":
        dutiesInformation = {
            "Type": "02",
            "BillReceiver": {
                "AccountNumber": shipmentData['dutiesAndTaxesInformation']['accountNumber'],
                "Address": {
                    "PostalCode": shipmentData['dutiesAndTaxesInformation']['postalCode']
                }
            }
        }
    elif (shipmentData['dutiesAndTaxesInformation']['paymentMethod']) == "04":
        dutiesInformation = {
            "Type": "02",
            "BillThirdParty	": {
                "AccountNumber": shipmentData['dutiesAndTaxesInformation']['accountNumber'],
                "Address": {
                    "PostalCode": shipmentData['dutiesAndTaxesInformation']['postalCode'],
                    "CountryCode": shipmentData['dutiesAndTaxesInformation']['countryCode']
                }
            }
        }
    print(paymentChargeInformation)
    print(dutiesInformation)
    shipmentCharge = []
    shipmentCharge.append(paymentChargeInformation)
    shipmentCharge.append(dutiesInformation)
    paymentInformation = {
        "ShipmentCharge":
            shipmentCharge
    }
    payload = {
        "ShipmentRequest": {
            "Request": {
                "SubVersion": "1801",
                "RequestOption": "nonvalidate",
                "TransactionReference": {
                    "CustomerContext": ""
                }
            },
            "Shipment": {
                # "Description": "",
                "Description": shipmentData['description'],

                "Shipper": {
                    "Name": fromlocation.fullName,
                    "AttentionName": fromlocation.attentionName,
                    "TaxIdentificationNumber": shipmentData['customData']['taxId'],
                    "Phone": {
                        "Number": fromlocation.phone
                    },
                    "Address": {
                        "AddressLine": fromlocation.address,
                        "City": fromlocation.city,
                        "StateProvinceCode": fromlocation.stateCode,
                        "PostalCode": fromlocation.postalCode,
                        "CountryCode": fromlocation.countryCode
                    },

                    "ShipperNumber": shipperlocation.shipperno,
                    "FaxNumber": shipperlocation.fax,
                },
                "ShipTo": {
                    "Name": shipmentData['recipient'],
                    "AttentionName": shipmentData['attention'],
                    "TaxIdentificationNumber": shipmentData['taxId'],
                    "Phone": {
                        "Number": shipmentData['phone']
                    },
                    "Address": {
                        "AddressLine": shipmentData['street'],
                        "City": shipmentData['city'],
                        "StateProvinceCode": shipmentData['state'],
                        "PostalCode": shipmentData['zip'],
                        "CountryCode": shipmentData['country_iso2']
                    },
                    "Residential": ""
                },
                "ShipFrom": {
                    "Name": fromlocation.fullName,
                    "AttentionName": fromlocation.attentionName,
                    "TaxIdentificationNumber": shipmentData['customData']['taxId'],
                    "Phone": {
                        "Number": fromlocation.phone
                    },
                    "Address": {
                        "AddressLine": fromlocation.address,
                        "City": fromlocation.city,
                        "StateProvinceCode": fromlocation.stateCode,
                        "PostalCode": fromlocation.postalCode,
                        "CountryCode": fromlocation.countryCode
                    }
                },
                "PaymentInformation": paymentInformation,
                "Service": {
                    "Code": shipmentData['service_code'],
                    "Description": ""
                },
                "Package": {

                    "Packaging": {
                        "Code": shipmentData['package_code'],
                        # "Description": "Nails"
                    },
                    "Dimensions": {
                        "UnitOfMeasurement": {
                            "Code": "IN" if shipmentData['weight_code'] == "LBS" else "CM",
                            "Description": "Inches" if shipmentData['weight_code'] == "LBS" else "CM",
                        },
                        "Length": str(shipmentData['length']),
                        "Width": str(shipmentData['width']),
                        "Height": str(shipmentData['height'])
                    },
                    "PackageWeight": {
                        "UnitOfMeasurement": {
                            "Code": shipmentData['weight_code'],
                            "Description": "Pounds" if shipmentData['weight_code'] == "LBS" else ""
                        },
                        "Weight": shipmentData['weight']
                    },
                    "PackageServiceOptions": {
                        "DeclaredValue": {
                            "CurrencyCode": shipmentData['internationalForm']['curCode'],
                            "MonetaryValue": str(shipmentData['declared_value']) if str(shipmentData['declared_value']) != "" else "0"
                        }
                    }
                }
            },
            "LabelSpecification": {
                "LabelImageFormat": {
                    "Code": "PNG",
                    "Description": "PNG"
                },
                "HTTPUserAgent": "Mozilla/4.5"
            }
        }
    }
    if (fromlocation.countryCode != shipmentData['country_iso2']):
        payload["ShipmentRequest"]["Shipment"]["ShipmentServiceOptions"] = serviceOptions
        payload["ShipmentRequest"]["Shipment"]["Description"] = shipmentData['description']
    headers = {
        "Content-Type": "application/json",
        "transId": str(uuid.uuid4()),
        "transactionSrc": "testing",
        "Authorization": "Bearer "+carrieruser.access_token
    }
    response = requests.post(
        url, json=payload, headers=headers, params=query)
    data = response.json()
    if 'response' in data and 'errors' in data['response'] and data['response']['errors']:
        return JsonResponse({"data": data['response']['errors'][0]['message']}, status=status.HTTP_400_BAD_REQUEST)
    try:
        shipment = Shipment.objects.get(userId=user_id, order=order)
    except:
        shipment = Shipment(userId=user_id, order=order)
    image_data = data["ShipmentResponse"]["ShipmentResults"]["PackageResults"][
        "ShippingLabel"]["GraphicImage"]
    if 'ShipmentResponse' in data and 'ShipmentResults' in data['ShipmentResponse'] and 'Form' in data['ShipmentResponse']['ShipmentResults']:
        invoice_data = data["ShipmentResponse"]["ShipmentResults"]["Form"][
            "Image"]["GraphicImage"]
    else:
        invoice_data = ""
    trackingnumber = data["ShipmentResponse"]["ShipmentResults"]["ShipmentIdentificationNumber"]
    print(data)
    if "LabelURL" in data["ShipmentResponse"]["ShipmentResults"]:
        labelurl = data["ShipmentResponse"]["ShipmentResults"]['LabelURL']
    else:
        labelurl = ""
    shipment.image = image_data
    shipment.carrier = "UPS"
    shipment.accountNumber = accountNumber
    shipment.trackingnumber = trackingnumber
    shipment.trackingurl = labelurl
    shipment.invoice = invoice_data
    shipment.save()
    return JsonResponse({"data": "Label Created", "carrier": "UPS", "trackingnumber": trackingnumber, "trackingurl": labelurl}, status=status.HTTP_200_OK)


@api_view(['POST'])
def addTax(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        tax = Taxes.objects.get(
            userId=user_id, nickname=user_data['taxData']['nickname'])
        return JsonResponse({'result': 'failed', 'data': 'Nickname exists'}, status=status.HTTP_404_NOT_FOUND)
    except Taxes.DoesNotExist:
        tax = Taxes(userId=user_id, nickname=user_data['taxData']['nickname'])
    tax.idType = user_data['taxData']['idType']
    tax.authority = user_data['taxData']['authority']
    tax.number = user_data['taxData']['number']
    tax.nickname = user_data['taxData']['nickname']
    tax.description = user_data['taxData']['description']
    tax.save()
    return JsonResponse({'result': 'success'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def deleteTax(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        tax = Taxes.objects.get(userId=user_id, nickname=user_data['nickname'])
    except Taxes.DoesNotExist:
        return JsonResponse({'result': 'failed', 'data': 'Tax not exists'}, status=status.HTTP_404_NOT_FOUND)
    except:
        return JsonResponse({'result': 'failed', 'data': 'Tax nicknames duplicated'}, status=status.HTTP_400_BAD_REQUEST)
    tax.delete()
    return JsonResponse({'result': 'success'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getTaxes(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    taxes = Taxes.objects.filter(Q(userId=user_id))

    taxes_dict = []
    for tax in taxes:
        tax_dict = {
            'id': tax.id,
            'userId': tax.userId,
            'idType': tax.idType,
            'authority': tax.authority,
            'number': tax.number,
            'nickname': tax.nickname,
            'description': tax.description,
            # Add more fields as needed
        }
        taxes_dict.append(tax_dict)
    # Create a JSON object containing the list of dictionaries
    json_data = json.dumps({'result': 'success', 'data': taxes_dict})
    return JsonResponse(json_data, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def saveInternationalSettings(request):
    user_data = JSONParser().parse(request)

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        setting = InternationalSettings.objects.get(
            userId=user_id)
    except:
        setting = InternationalSettings(
            userId=user_id)

    setting.defaultContentType = user_data['internationalData']['defaultContentType']
    setting.termsOfSale = user_data['internationalData']['termsOfSale']
    setting.declarationStatement = user_data['internationalData']['declarationStatement']
    setting.save()
    return JsonResponse({'result': 'success'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getInternationalSettings(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        internationalSettings = InternationalSettings.objects.get(
            userId=user_id)
    except InternationalSettings.DoesNotExist:
        internationalSettings = InternationalSettings(userId=user_id)
    return_data = {
        'userId': internationalSettings.userId,
        'defaultContentType': internationalSettings.defaultContentType,
        'termsOfSale': internationalSettings.termsOfSale,
        'declarationStatement': internationalSettings.declarationStatement,

    }
    json_data = json.dumps({'result': 'success', 'data': return_data})
    return JsonResponse(json_data, status=status.HTTP_200_OK, safe=False)


@api_view(['POST'])
def getAddress(request):
    user_data = JSONParser().parse(request)
    apiKey = user_data['apiKey']
    address = user_data['address']
    url = "https://autocomplete.search.hereapi.com/v1/autocomplete?q=" + \
        address+",&apiKey="+apiKey
    response = requests.get(url)

    if response.status_code == 200:
        # Handle successful response
        data = response.json()
        return JsonResponse({'result': 'success', 'data': data}, status=status.HTTP_200_OK, safe=False)
        # Do something with data
    else:
        # Handle error response
        return JsonResponse({'result': 'failed'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def addressValidation(request):
    user_data = JSONParser().parse(request)
    apiKey = user_data['apiKey']
    address = user_data['address']
    url = "https://autocomplete.search.hereapi.com/v1/geocode?q=" + \
        address+",&apiKey="+apiKey
    response = requests.get(url)

    if response.status_code == 200:
        # Handle successful response
        data = response.json()
        return JsonResponse({'result': 'success', 'data': data}, status=status.HTTP_200_OK, safe=False)
        # Do something with data
    else:
        # Handle error response
        return JsonResponse({'result': 'failed'}, status=status.HTTP_400_BAD_REQUEST)


ups_refreshtoken_endpoint = "https://wwwcie.ups.com/security/v1/oauth/refresh"


def fetchToken():

    carrierUsers = CarrierUsers.objects.all()
    for carrierUser in carrierUsers:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": carrierUser.refresh_token
        }
        auth_str = f"{settings.UPS_CLIENT_ID}:{settings.UPS_CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_b64}"
        }
        response = requests.post(ups_refreshtoken_endpoint,
                                 data=payload, headers=headers)
        if (response):
            data = response.json()
            carrierUser.status = data['status']
            carrierUser.access_token = data['access_token']
            carrierUser.refresh_token = data['refresh_token']
            carrierUser.save()  # Save the new object to the database
            print("saved")
        time.sleep(10)


def authenticate_and_refresh_token(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        carrierUsers = CarrierUsers.objects.all()
        # Sort the CarrierUsers objects by accountNumber
        sorted_carrierUsers = sorted(
            carrierUsers, key=lambda x: x.accountNumber)

        # Group the sorted objects by accountNumber
        grouped_carrierUsers = itertools.groupby(
            sorted_carrierUsers, key=lambda x: x.accountNumber)

        # Iterate over the groups
        for accountNumber, group in grouped_carrierUsers:
            print(f"Account Number: {accountNumber}")
            for user in group:
                if is_token_expired(user.access_token):
                    remake_token(accountNumber, user.refresh_token)
                else:
                    print("FALSE")
        return view_func(request, *args, **kwargs)
    return wrapper


def remake_token(accountNumber, refreshToken):
    # Encode the authorization credentials as base64
    auth_str = f"{settings.UPS_CLIENT_ID}:{settings.UPS_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_b64}"
    }
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refreshToken
    }
    response = requests.post(settings.UPS_REFRESHTOKEN_ENDPOINT,
                             data=payload, headers=headers)

    try:
        carrierusers = CarrierUsers.objects.filter(accountNumber=accountNumber)
        for carrier_user in carrierusers:
            data = response.json()
            carrier_user.access_token = data['access_token']
            carrier_user.refresh_token = data['refresh_token']
            carrier_user.save()
    except CarrierUsers.DoesNotExist:
        return JsonResponse({'CarrierUser not exists': False}, status=status.HTTP_401_UNAUTHORIZED)


def is_token_expired(token):
    try:
        payload = jwt.decode(token, "",
                             algorithms=['HS256', 'RS384'], options={"verify_signature": False})
        return False
    except ExpiredSignatureError:
        return True
