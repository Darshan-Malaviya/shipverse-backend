from rest_framework.decorators import api_view
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.parsers import JSONParser
import requests
import json
from rest_framework import status
from shipverse.models import Shop, Users, Shipment
from shipverse.auth import getUserIdByToken
from shipverse.auth import decode_access_token
from datetime import datetime
import hmac
import hashlib
import base64
import secrets


def addshopifystore(request):
    hmac = request.GET.get('hmac')
    host = request.GET.get('host')
    shop = request.GET.get('shop')
    code = request.GET.get('code')

    scopes = 'write_orders,read_customers,read_assigned_fulfillment_orders,write_assigned_fulfillment_orders,read_fulfillments,write_fulfillments,read_merchant_managed_fulfillment_orders,write_merchant_managed_fulfillment_orders,read_third_party_fulfillment_orders,write_third_party_fulfillment_orders'
    if hmac is not None and host is not None and shop is not None:
        if code is None:
            return redirect('https://' + shop + '/admin/oauth/authorize?client_id=' + settings.SHOPIFY_CLIENT_ID +
                            '&scope=' + scopes + '&redirect_uri=' + settings.SHOPIFY_REDIRECT_URL)
        else:
            url = request.build_absolute_uri()
            modified_url = url.replace("http", "https")
            modified_url = modified_url.replace(
                settings.SHOPIFY_REDIRECT_URL, settings.FRONTEND_URL+"/application/settings/onboard")

            return redirect(modified_url)
    # return redirect('https://territorial.io')


@api_view(['POST'])
def getToken(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    auth_code = user_data['code']
    shopify_domain = user_data['shop']
    shopify_token_endpoint = user_data['shopify_token_endpoint']
    try:
        shop = Shop.objects.get(userId=user_id,
                                shopify_domain=shopify_domain)
    except Shop.DoesNotExist:
        shop = Shop(userId=user_id, shopify_domain=shopify_domain)
    payload = {
        "client_id": settings.SHOPIFY_CLIENT_ID,
        "client_secret": settings.SHOPIFY_CLIENT_SECRET,
        "code": auth_code
    }
    print(payload)
    try:
        response = requests.post(shopify_token_endpoint, data=payload)
        data = response.json()
        shop.shopify_domain = shopify_domain
        shop.shopify_token = data['access_token']
        shop.save()

        return JsonResponse({"result": True, 'data': {'domain': shop.shopify_domain}}, status=status.HTTP_200_OK)
    except:
        return JsonResponse({"result": False}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def getShopifyStores(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        shopifyStores = Shop.objects.filter(userId=user_id)
    except Shop.DoesNotExist:
        return JsonResponse({"result": True, 'data': []}, status=status.HTTP_200_OK)
    stores = []
    for shopifyStore in shopifyStores:

        endpoint = "https://"+shopifyStore.shopify_domain+"/admin/oauth/access_scopes.json"
        headers = {
            "X-Shopify-Access-Token": shopifyStore.shopify_token
        }
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 401 or response.status_code == 403:
            shopifyStore.delete()
            continue
        store = {
            'domain': shopifyStore.shopify_domain,
        }
        apiVersion = "2023-07"
        stores.append(store)
    json_data = json.dumps({'stores': stores})
    return JsonResponse({"result": True, 'data': stores}, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def getProducts(request):


@api_view(['POST'])
def getOrders(request):
    order_data = []
    user_data = JSONParser().parse(request)
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    destination = user_data['destination']
    storeName = user_data['storeName']
    if user_id == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Unregistered User'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        storeuser = Shop.objects.get(userId=user_id, shopify_domain=storeName)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.shopify_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    apiVersion = "2023-07"

    # endpoint = "https://"+storeuser.shopify_domain + \
    #     "/admin/api/"+apiVersion+"/orders.json"
    # headers = {
    #     "X-Shopify-Access-Token": storeuser.shopify_token
    # }
    # response = requests.get(endpoint, headers=headers)
    # orders = response.json()['orders']
    orders = []
    limit_orders = '25'
    destination = user_data['destination']
    for status_id in user_data['orderStates']:
        endpoint = ""
        headers = {
            "X-Shopify-Access-Token": storeuser.shopify_token
        }
        if status_id == '7':  # awaiting payment
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders.json?status=open&financial_status=pending,partially_paid,unpaid,authorized&fulfillment_status=unfulfilled"+"&limit="+limit_orders
            response = requests.get(endpoint, headers=headers)
            orders.extend(response.json()['orders'])
        elif status_id == '11':  # awaiting fulfillment
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders.json?status=open&fulfillment_status=unfulfilled&financial_status=paid,partially_refunded" + \
                "&limit="+limit_orders
            response = requests.get(endpoint, headers=headers)
            orders.extend(response.json()['orders'])
        elif status_id == '5':  # Cancelled
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion+"/orders.json?status=cancelled"+"&limit="+limit_orders
            response = requests.get(endpoint, headers=headers)
            orders.extend(response.json()['orders'])
        elif status_id == '13':  # On Hold
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders.json?status=open&financial_status=pending" + \
                "&limit="+limit_orders+"&fulfillment_status="
            response = requests.get(endpoint, headers=headers)
            pending_orders_with_onhold = response.json()['orders']
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders.json?status=open&financial_status=pending&fulfillment_status=unfulfilled" + \
                "&limit="+limit_orders
            response = requests.get(endpoint, headers=headers)
            pending_orders_without_onhold = response.json()['orders']
            subtracted_list = [
                x for x in pending_orders_with_onhold if x not in pending_orders_without_onhold]
            orders.extend(subtracted_list)
        elif status_id == '2':  # Shipped
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders.json?status=any&fulfillment_status=shipped"+"&limit="+limit_orders
            response = requests.get(endpoint, headers=headers)
            orders.extend(response.json()['orders'])
    # print(orders)
    new_list = []

    for order in orders:
        if order not in new_list:
            new_list.append(order)
    orders = new_list
    for order in orders:

        date_obj = datetime.strptime(
            order['created_at'], "%Y-%m-%dT%H:%M:%S%z")
        current_date = datetime.now()
        naive = date_obj.replace(tzinfo=None)
        time_difference = current_date - naive
        days_difference = time_difference.days
        sku = ""
        itemname = order['line_items'][0]['name']
        billing_address = order['billing_address']
        if destination == "Domestic":
            if billing_address is None:
                continue
            if billing_address['country_code'] != "CA":
                continue
        if destination == "International":
            if billing_address is None:
                continue
            if billing_address['country_code'] == "CA":
                continue
        product_data = []
        for data in order['line_items']:
            product_dict = {
                'id': data['product_id'],
                'description': data['name'],
                'sku': data['sku'],
                'quantity': data['quantity'],
                'value': data['price'],
                'countryCode': "" if billing_address is None else billing_address['country_code'],
                'harmonisation': ""
            }
            product_data.append(product_dict)
            sku = sku + "" if data['sku'] is None else data['sku'] + " "

        haslabel = "false"
        hasinvoice = "false"
        try:
            shipment = Shipment.objects.get(
                userId=user_id, order=order['order_number'])
            if shipment.image != "":
                haslabel = "true"
            if shipment.invoice != "":
                hasinvoice = "true"
        except:
            haslabel = "false"
            hasinvoice = "false"
        order_dict = {
            'id': str(order['order_number']),
            'order_id': str(order['id']),
            'date_created': str(date_obj.strftime("%d/%m/%Y")),
            'age': days_difference,
            'orderstatus': order['financial_status'],
            'fulfillment_status': order['fulfillment_status'],
            'itemname': itemname,
            'recipient': "" if billing_address is None else billing_address['first_name'] + " " + billing_address['last_name'],
            'attention': "" if billing_address is None else billing_address['company'],
            'street': "" if billing_address is None else billing_address['address1'],
            'city': "" if billing_address is None else billing_address['city'],
            'state': "" if billing_address is None else billing_address['province'],
            'country': "" if billing_address is None else billing_address['country'],
            'country_iso2': "" if billing_address is None else billing_address['country_code'],
            'phone': "" if billing_address is None else billing_address['phone'],
            'zip': "" if billing_address is None else billing_address['zip'],
            'sku': sku,
            'items_total': order['total_line_items_price'],
            'total_ex_tax': order['total_tax'],
            'label': haslabel,
            'invoice': hasinvoice,
            'itn': "",
            'taxId': "",
            'products': product_data,
            'shoptype': "shopify",
            'storename': storeName
            # add more fields as needed
        }
        order_data.append(order_dict)
    json_data = json.dumps(order_data)

    return JsonResponse(json_data, safe=False)


@api_view(['POST'])
def update2shipment(request):
    user_data = JSONParser().parse(request)
    order_ids = user_data['orders']
    status_text = user_data['text']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    storeName = user_data['storeName']
    try:
        storeuser = Shop.objects.get(userId=user_id, shopify_domain=storeName)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.shopify_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    apiVersion = "2023-07"
    print(order_ids)
    for order_id in order_ids:
        if status_text == "Awaiting Payment":
            return JsonResponse({"success": "true"})
        elif status_text == "On Hold":
            return JsonResponse({"success": "true"})
        elif status_text == "Awaiting Fulfillment":
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders/"+order_id+"/transactions.json"
            headers = {
                "X-Shopify-Access-Token": storeuser.shopify_token,
                "Content-Type": "application/json"
            }
            datas = {
                "transaction":
                {
                    "kind": "sale",
                    "status": "success",
                    "source": "external"
                }
            }
            response = requests.post(endpoint, json=datas, headers=headers)
        elif status_text == "Cancelled":
            endpoint = "https://"+storeuser.shopify_domain + \
                "/admin/api/"+apiVersion + \
                "/orders/"+order_id+"/cancel.json"
            headers = {
                "X-Shopify-Access-Token": storeuser.shopify_token
            }
            response = requests.post(endpoint, data={}, headers=headers)

    return JsonResponse({"success": "true"}, status=200)


@api_view(['POST'])
def markasshipped(request):
    user_data = JSONParser().parse(request)
    order_ids = user_data['orders']
    carrier = user_data['carrier']
    tracking_number = user_data['tracking_number']
    tracking_url = user_data['tracking_url']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    storeName = user_data['storeName']
    try:
        storeuser = Shop.objects.get(userId=user_id, shopify_domain=storeName)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.shopify_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    apiVersion = "2023-07"
    for order_id in order_ids:
        headers = {
            "X-Shopify-Access-Token": storeuser.shopify_token
        }
        endpoint = "https://"+storeuser.shopify_domain + \
            "/admin/api/"+apiVersion + \
            "/orders/" + order_id + "/fulfillment_orders.json"
        response = requests.get(endpoint, headers=headers)
        fulfillment_orders = response.json()['fulfillment_orders']
        print(fulfillment_orders)
        endpoint = "https://"+storeuser.shopify_domain + \
            "/admin/api/"+apiVersion + \
            "/fulfillments.json"
        headers = {
            "X-Shopify-Access-Token": storeuser.shopify_token,
            "Content-Type": "application/json"
        }
        line_items = [{"fulfillment_order_id": fulfillment_order['id']}
                      for fulfillment_order in fulfillment_orders]
        for line_item in line_items:
            datas = {
                "fulfillment":
                {
                    "line_items_by_fulfillment_order": [line_item],
                    "tracking_info": {
                        "company": carrier,
                        "number": tracking_number,
                        "url": tracking_url
                    }
                }
            }
            print(endpoint)
            response = requests.post(endpoint, json=datas, headers=headers)
        if 'errors' in response.json():
            return JsonResponse({"success": "false", "data": response.json()['errors']}, status=500)
    return JsonResponse({"success": "true"}, status=200)


@api_view(['POST'])
def removestore(request):
    user_data = JSONParser().parse(request)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    storeName = user_data['storeName']
    try:
        storeuser = Shop.objects.get(userId=user_id, shopify_domain=storeName)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)

    if storeuser.shopify_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    headers = {
        "X-Shopify-Access-Token": storeuser.shopify_token
    }
    endpoint = "https://"+storeuser.shopify_domain + \
        "/admin/api_permissions/current.json"

    response = requests.delete(endpoint, headers=headers)
    status_code = response.status_code
    print(status_code)
    if status_code != 200:
        return JsonResponse({"success": "false", "data": response.json()['errors']}, status=500)
    storeuser.delete()
    return JsonResponse({"success": "true", "data": "success"}, status=200)


CLIENT_SECRET = 'my_client_secret'


def verify_webhook(data, hmac_header):
    digest = hmac.new(CLIENT_SECRET.encode('utf-8'), data,
                      digestmod=hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest)

    return hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8'))


@api_view(['POST'])
def data_request_webhook(request):
    data = request.body
    verified = verify_webhook(
        data, request.headers.get('X-Shopify-Hmac-SHA256'))

    if not verified:
        return HttpResponse(status=401)

    # Process webhook payload
    # ...
    return HttpResponse(status=200)


@api_view(['POST'])
def customer_redact_webhook(request):
    data = request.body
    verified = verify_webhook(
        data, request.headers.get('X-Shopify-Hmac-SHA256'))

    if not verified:
        return HttpResponse(status=401)

    # Process webhook payload
    # ...
    return HttpResponse(status=200)


@api_view(['POST'])
def shop_redact_webhook(request):
    data = request.body
    verified = verify_webhook(
        data, request.headers.get('X-Shopify-Hmac-SHA256'))

    if not verified:
        return HttpResponse(status=401)

    # Process webhook payload
    # ...
    return HttpResponse(status=200)
