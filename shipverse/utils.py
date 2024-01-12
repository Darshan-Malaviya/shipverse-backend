from .auth import getUserIdByToken
from .models import *
from .response import func_response

def CheckReturnOnBoard(user_id : str):

    if StoreUsers.objects.filter(userId=f"{user_id}").count() == 0 or CarrierUsers.objects.filter(userId=f"{user_id}").count() == 0 or FromLocation.objects.filter(userId=f"{user_id}").count() == 0 :
        return False
    else: return True


def get_authenticated_user(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    if auth_header:
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id, isEmailVerified=True)
        return user
    else:
        raise Exception("Authorization token not found!")


def get_sender_info(user, user_carrier, from_location):
        return {
            "name": user.username,
            "company": user_carrier.company_name,
            "contact-phone": user.phone,
            "address-details": {
                "address-line-1": from_location.address or from_location.address1,
                "city": from_location.city,  
                "prov-state": from_location.stateCode, 
                "country-code": from_location.countryCode,  
                "postal-zip-code": from_location.postalCode,  
            }
        }


def get_receiver_info(data):
        sold_to = data.get("shipmentData", {}).get("soldTo", {})
        return {
            "name": data.get("shipmentData", {}).get("recipient"),
            "company": sold_to.get("companyName") or sold_to.get("attentionName"),
            "client-voice-number": sold_to.get("phone"),
            "address-details": {
                "address-line-1": sold_to.get("street"),
                "city": sold_to.get("city"),
                "prov-state": sold_to.get("stateCode"),
                "country-code": sold_to.get("countryCode"),
                "postal-zip-code": sold_to.get("postalCode")
            }
        }


def get_parcel_info(data):
        return {
            "weight": data.get("shipmentData", {}).get("weight"),
            "dimensions": {
                "length": data.get("shipmentData", {}).get("length"),
                "width": data.get("shipmentData", {}).get("width"),
                "height": data.get("shipmentData", {}).get("height"),
            },
            "mailing-tube": "false",
        }


def get_options(data):
        service_code = data.get("shipmentData", {}).get("service_code")
        insurance_value = data.get("shipmentData", {}).get("declared_value")
        non_delivery_handling = data.get("shipmentData", {}).get("internationalForm", {}).get("nonDelivery")
        delivery_codes = ["RASE", "RTS", "ABAN"]
        options = []
        if insurance_value:
            options.append({
                "option-code": "COV",
                "option-amount": insurance_value
            })
        if not service_code.startswith("DOM") or (non_delivery_handling in delivery_codes):
            options.append({
                "option-code": non_delivery_handling
            })    
        return options
        

def get_customs_info(data):
    products = data.get("shipmentData", {}).get("products")
    weight = int(data.get("shipmentData", {}).get("weight"))
    print("weight", weight)
    unit_weight = float(int((int(data.get("shipmentData", {}).get("weight")) / len(products))))
    print("unit weight", unit_weight)
    sku_list = ""
    for product in products:
        sku_list += f'''
            <item>
                <customs-description>{product.get("description")}</customs-description>
                <sku>{product.get("sku")}</sku>
                <customs-number-of-units>{product.get("quantity")}</customs-number-of-units>
                <unit-weight>{unit_weight/product.get("quantity")}</unit-weight>
                <customs-value-per-unit>{product.get("value")}</customs-value-per-unit>
            </item>
        '''
        value = float(product.get("value"))
        # print("value", type(value))
    reason_for_export = data.get("shipmentData", {}).get("internationalForm", {}).get("reasonForExport")
    currency_code = data.get("shipmentData", {}).get("internationalForm", {}).get("curCode")
    # value = data.get("shipmentData", {}).get("products", {}).get("value")
    # print("value", value)

    exchange_rates = {
        "CAD": 1.0,  # Canadian Dollar
        "USD": 0.75,  # Example: Exchange rate for USD
        "INR": 62.23,
        # "AFN": ,
        # "ALL": ,
        # "EUR": ,
        # "ARS": ,
        # "AUD": ,
        # "BHD": ,
        # "BDT": ,
        # "CNY": ,
        # "COP": ,
        # "CZK": ,
        # Add more currencies and their exchange rates as needed
    }
    conversion_rate = exchange_rates.get(currency_code, None)
    if conversion_rate is not None:
        value_in_foreign_currency = value * conversion_rate
    else:
        value_in_foreign_currency = None

    return {
        "currency": currency_code,
        "conversion-from-cad": value_in_foreign_currency,
        "reason-for-export": reason_for_export,
        "other-reason": "",
        "sku-list": sku_list,
    }


def build_shipment_payload(
        group_id, shipping_request_point, service_code, sender_info, receiver_info, parcel_info, options,
        notification_email, customs_info, settlement_info):

        payload = f"""<shipment xmlns="http://www.canadapost.ca/ws/shipment-v8">
                        <group-id>{group_id}</group-id>
                        <requested-shipping-point>{shipping_request_point.replace(" ","")}</requested-shipping-point>
                        <delivery-spec>
                            <service-code>{service_code}</service-code>
                            <sender>
                                <name>{sender_info['name']}</name>
                                <company>{sender_info['company']}</company>
                                <contact-phone>{sender_info['contact-phone']}</contact-phone>
                                <address-details>
                                    <address-line-1>{sender_info['address-details']['address-line-1']}</address-line-1>
                                    <city>{sender_info['address-details']['city']}</city>
                                    <prov-state>{sender_info['address-details']['prov-state']}</prov-state>
                                    <country-code>{sender_info['address-details']['country-code']}</country-code>
                                    <postal-zip-code>{sender_info['address-details']['postal-zip-code'].replace(" ","")}</postal-zip-code>
                                </address-details>
                            </sender>
                            <destination>
                                <name>{receiver_info['name']}</name>
                                <company>{receiver_info['company']}</company>
                                <client-voice-number>{receiver_info['client-voice-number']}</client-voice-number>
                                <address-details>
                                    <address-line-1>{receiver_info['address-details']['address-line-1']}</address-line-1>
                                    <city>{receiver_info['address-details']['city']}</city>
                                    <prov-state>{receiver_info['address-details']['prov-state']}</prov-state>
                                    <country-code>{receiver_info['address-details']['country-code']}</country-code>
                                    <postal-zip-code>{receiver_info['address-details']['postal-zip-code'].replace(" ","")}</postal-zip-code>
                                </address-details>
                            </destination>
                            """

        if options:
            payload += f"""<options>{''.join([f"<option><option-code>{opt['option-code']}</option-code>" +
                        (f"<option-amount>{opt['option-amount']}</option-amount>" if 'option-amount' in opt else '') +
                        '</option>' for opt in options])}</options>"""

        payload += f"""<parcel-characteristics>
                            <weight>{parcel_info['weight']}</weight>
                            <dimensions>
                                <length>{parcel_info['dimensions']['length']}</length>
                                <width>{parcel_info['dimensions']['width']}</width>
                                <height>{parcel_info['dimensions']['height']}</height>
                            </dimensions>
                            <mailing-tube>{parcel_info['mailing-tube']}</mailing-tube>
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
                            <show-postage-rate>true</show-postage-rate>
                            <show-insured-value>true</show-insured-value>
                        </preferences>
                        """
        if service_code.startswith("INT") or service_code.startswith("USA"):
            if customs_info:
                payload += f"""<customs>
                                <currency>{customs_info['currency']}</currency>
                                <conversion-from-cad>{customs_info['conversion-from-cad']}</conversion-from-cad>
                                <reason-for-export>{customs_info['reason-for-export']}</reason-for-export>
                                <other-reason>{customs_info['other-reason']}</other-reason>
                                <sku-list>{customs_info['sku-list']}</sku-list>
                            </customs>"""

        payload += f"""<settlement-info>
                            <contract-id>{settlement_info['contract_id']}</contract-id>
                            <intended-method-of-payment>{settlement_info['intended_method_of_payment']}</intended-method-of-payment>
                        </settlement-info>
                    </delivery-spec>
                </shipment>"""

        return payload


