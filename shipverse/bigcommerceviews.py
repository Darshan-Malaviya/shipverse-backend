import bigcommerce.api
import json
import requests
import jwt
from django.db.models import Q
from django.shortcuts import redirect
from datetime import datetime
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view
from shipverse.models import Users,  StoreUsers, Shipment
from rest_framework import status
from shipverse.auth import decode_access_token
from django.conf import settings


def addBigCommerceStore(request):
    code = request.GET.get('code')
    context = request.GET.get('context')
    scope = request.GET.get('scope')
    context_array = context.split("/")
    store_hash = context_array[1]
    if code is not None and context is not None and scope is not None:
        grant_type = 'authorization_code'
        # Make a POST request to the token endpoint with the credentials

        response = requests.post(settings.BC_TOKEN_ENDPOINT, data={
            'grant_type': grant_type,
            'code': code,
            'client_id': settings.BC_CLIENT_ID,
            'client_secret': settings.BC_CLIENT_SECRET,
            'redirect_uri': settings.BC_REDIRECT_URI,
        })
        print(response.status_code)
        access_token = response.json()['access_token']
        filter_count = StoreUsers.objects.filter(
            Q(storeHash=store_hash)).count()
        if filter_count == 0:
            store_user = StoreUsers()
        else:
            store_user = StoreUsers.objects.filter(
                Q(storeHash=store_hash)).first()

        store_user.access_token = access_token
        store_user.code = code
        store_user.storeHash = store_hash
        store_user.save()
    return redirect(settings.FRONTEND_URL+"/application/settings/onboard?bc_code="+code+"&store_hash="+store_hash)


def loadBigCommerceStore(request):
    return redirect(settings.FRONTEND_URL+"/application/settings/onboard")


def uninstallBigCommerceStore(request):
    signed_payload_jwt = request.GET.get('signed_payload_jwt')
    jwt_secret = settings.BC_CLIENT_SECRET
    decoded_token = jwt.decode(
        signed_payload_jwt, jwt_secret, audience=settings.BC_CLIENT_ID, algorithms="HS256",  options={"verify_exp": False, "verify_iat": False, "verify_nbf": False})
    decoded_store_hash = decoded_token['sub'].split('/')[1]
    try:
        store_user = StoreUsers.objects.get(storeHash=decoded_store_hash)
    except StoreUsers.DoesNotExist:
        return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)
    store_user.delete()
    return JsonResponse({}, status=status.HTTP_200_OK)


@api_view(['POST'])
def saveUserId(request):
    user_data = JSONParser().parse(request)
    # Set JWT token
    code = user_data['code']
    store_hash = user_data['store_hash']
    print(code, store_hash)
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    if StoreUsers.objects.filter(Q(storeHash=store_hash) & Q(code=code)).count() == 0:
        return JsonResponse({'success': 'FALSE'})
    else:
        store_user = StoreUsers.objects.filter(
            Q(storeHash=store_hash) & Q(code=code)).first()
    store_user.userId = user_id
    store_user.save()
    return JsonResponse({'success': "TRUE"})


@api_view(['POST'])
def get_isAuth(request):
    # Get the authorization code from the query string
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    try:
        storeuser = StoreUsers.objects.get(userId=user_id)
    except StoreUsers.DoesNotExist:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    if storeuser.access_token.strip() == "" or not storeuser.access_token:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return JsonResponse({'isAuthorized': True})


@api_view(['POST'])
def disconnect(request):
    # Get the authorization code from the query string
    # Get the access token from the Authorization header
    user_data = JSONParser().parse(request)
    storeHash = user_data['storeHash']
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    try:
        storeuser = StoreUsers.objects.filter(
            Q(userId=user_id) | Q(storeHash=storeHash)).first()
    except:
        return JsonResponse({'StoreUser do not exists': False}, status=status.HTTP_401_UNAUTHORIZED)
    storeuser.access_token = ""
    storeuser.save()
    return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def get_orders(request):
    order_data = []
    user_data = JSONParser().parse(request)
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']

    if user_id == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Unregistered User'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        storeuser = StoreUsers.objects.filter(userId=user_id).first()
    except StoreUsers.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.access_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    # api = bigcommerce.api.BigcommerceApi(client_id=settings.BC_CLIENT_ID,
        #  store_hash=storeuser.storeHash, access_token=storeuser.access_token)
    destination = user_data['destination']
    parsed_results = []

    for order_status in user_data['orderStates']:
        parsed_results.extend(mapOrderStatus(order_status))
    limit_orders = '25'
    orders = []
    for status_id in parsed_results:
        # GET ORDERS
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Token": storeuser.access_token
        }
        endpoint = "https://api.bigcommerce.com/stores/" + \
            storeuser.storeHash+"/v2/orders?status_id=" + \
            status_id + "&limit="+limit_orders+"&sort=date_created:desc"
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            status_orders = response.json()
            orders.extend(status_orders)
        # status_orders = api.Orders.all(status_id=status_id)
    for order in orders:
        try:
            date_obj = datetime.strptime(
                order['date_created'], "%a, %d %b %Y %H:%M:%S %z")
        except:
            continue
        current_date = datetime.now()
        naive = date_obj.replace(tzinfo=None)
        time_difference = current_date - naive
        days_difference = time_difference.days

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Token": storeuser.access_token
        }
        endpoint = "https://api.bigcommerce.com/stores/" + \
            storeuser.storeHash+"/v2/orders/"+str(order['id'])+"/products"
        response = requests.get(endpoint, headers=headers)
        datas = response.json()
        sku = ""
        itemname = datas[0]['name']
        billing_address_json = json.dumps(order['billing_address'])
        billing_address = json.loads(billing_address_json)

        if destination == "Domestic":
            if billing_address['country_iso2'] != "CA":
                continue
        if destination == "International":
            if billing_address['country_iso2'] == "CA":
                continue

        product_data = []
        for data in datas:
            product_dict = {
                'id': data['id'],
                'description': data['name'],
                'sku': data['sku'],
                'quantity': data['quantity'],
                'value': data['base_price'],
                'countryCode': billing_address['country_iso2'],
                'harmonisation': ""
            }
            product_data.append(product_dict)
            sku = sku + data['sku'] + " "

        haslabel = "false"
        hasinvoice = "false"
        try:
            shipment = Shipment.objects.get(
                userId=user_id, order=order['id'])
            if shipment.image != "":
                haslabel = "true"
            if shipment.invoice != "":
                hasinvoice = "true"
        except:
            haslabel = "false"
            hasinvoice = "false"
        order_dict = {
            'id': str(order['id']),
            'order_id': str(order['id']),
            'date_created': str(date_obj.strftime("%d/%m/%Y")),
            'age': days_difference,
            'orderstatus': order['status'],
            'itemname': itemname,
            'recipient': billing_address['first_name'] + " " + billing_address['last_name'],
            'attention': billing_address['company'],
            'street': billing_address['street_1'],
            'city': billing_address['city'],
            'state': billing_address['state'],
            'country': billing_address['country'],
            'country_iso2': billing_address['country_iso2'],
            'phone': billing_address['phone'],
            'zip': billing_address['zip'],
            'sku': sku,
            'items_total': order['items_total'],
            'total_ex_tax': order['total_ex_tax'],
            'label': haslabel,
            'invoice': hasinvoice,
            'itn': "",
            'taxId': "",
            'products': product_data,
            'shoptype': "bigcommerce",
            'storename': ""
            # add more fields as needed
        }
        order_data.append(order_dict)
    json_data = json.dumps(order_data)

    return JsonResponse(json_data, safe=False)


@api_view(['POST'])
def update2shipment(request):
    user_data = JSONParser().parse(request)
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    orders = user_data.get('orders')
    status_id = user_data.get('status_id')
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Unregistered User'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        storeuser = StoreUsers.objects.get(userId=user_id)
    except StoreUsers.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.access_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    api = bigcommerce.api.BigcommerceApi(client_id=settings.BC_CLIENT_ID,
                                         store_hash=storeuser.storeHash, access_token=storeuser.access_token)

    for orderid in orders:
        order = api.Orders.get(id=orderid)
        order.update(status_id=status_id)
    return JsonResponse({"success": "true"})


@api_view(['POST'])
def markasshipped(request):
    user_data = JSONParser().parse(request)
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    orders = user_data.get('orders')
    status_id = user_data.get('status_id')
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Unregistered User'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        storeuser = StoreUsers.objects.get(userId=user_id)
    except StoreUsers.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.access_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    api = bigcommerce.api.BigcommerceApi(client_id=settings.BC_CLIENT_ID,
                                         store_hash=storeuser.storeHash, access_token=storeuser.access_token)

    for orderid in orders:
        order = api.Orders.get(id=orderid)
        order.update(status_id=2)
    return JsonResponse({"success": "true"})


@api_view(['POST'])
def getBigCommerceStores(request):
    # Get the authorization code from the query string
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']
    try:
        storeusers = StoreUsers.objects.filter(userId=user_id)
    except:
        return JsonResponse({'StoreUser do not exists': False}, status=status.HTTP_401_UNAUTHORIZED)
    storenames = []
    for storeuser in storeusers:
        if storeuser.storeHash is not None and storeuser.access_token is not None:
            url = "https://api.bigcommerce.com/stores/"+storeuser.storeHash+"/v2/store"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Auth-Token": storeuser.access_token
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            storenames.append(data)
    return JsonResponse({'result': 'success', 'data': storenames}, status=status.HTTP_200_OK)


@api_view(['POST'])
def getProducts(request):
    user_data = JSONParser().parse(request)
    # Get the access token from the Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    access_token = auth_header
    token_data = decode_access_token(access_token)
    user_id = token_data['user_id']

    if user_id == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Unregistered User'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        storeuser = StoreUsers.objects.get(userId=user_id)
    except StoreUsers.DoesNotExist:
        return JsonResponse({'error': 'Unregistered StoreUser'}, status=status.HTTP_401_UNAUTHORIZED)
    if storeuser.access_token == "":
        return JsonResponse({'isAuthorized': False}, status=status.HTTP_401_UNAUTHORIZED)

    api = bigcommerce.api.BigcommerceApi(client_id=settings.BC_CLIENT_ID,
                                         store_hash=storeuser.storeHash, access_token=storeuser.access_token)
    products = api.Products.all()
    products_data = []

    for product in products:
        width = float(product['width'])
        height = float(product['height'])
        depth = float(product['depth'])
        date_obj = datetime.strptime(
            product['date_modified'], "%a, %d %b %Y %H:%M:%S %z")
        dateModified = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        date_obj = datetime.strptime(
            product['date_created'], "%a, %d %b %Y %H:%M:%S %z")
        dateCreated = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        product_dict = {
            'id': product['id'],
            'sku': product['sku'],
            'weight': product['weight'],
            'name': product['name'],
            'date_created': dateCreated,
            'image_url': product['primary_image']['standard_url'],
            'availability': product['availability'],
            'cost_price': product['cost_price'],
            'dimensions': str(width)+"*"+str(height)+"*"+str(depth),
            # 'upc': product['upc'],
            # 'categories': "",  # product['categories'],
            'date_modified': dateModified,
            # 'sku': data['sku'],
            # 'quantity': data['quantity'],
            # 'value': data['base_price'],
            # 'countryCode': billing_address['country_iso2'],
            # 'harmonisation': ""
        }
        products_data.append(product_dict)
    json_data = json.dumps(products_data)

    return JsonResponse({"result": "success", "data": json_data}, safe=False)


def mapOrderStatus(status):
    result = []
    if status == '11':
        result = ['3', '8', '9', '11', '0']
    elif status == '7':
        result = ['1', '7']
    elif status == '5':
        result = ['5', '6']
    elif status == '13':
        result = ['13', '12']
    elif status == '2':
        result = ['2', '4', '10', '14']
    return result
