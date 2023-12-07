from __future__ import print_function
import base64

from django.http.response import JsonResponse
import requests
import xmltodict
from .models import UserCarrier
from .decorators import log_api_activity
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from shipverse.models import Users, VerificationTokens, ResetPasswordTokens, InviteTokens, Subscriptions
from rest_framework.decorators import api_view
import re
import json
from django.core.mail import send_mail
from DjangoRestApisPostgreSQL import settings
from django.conf import settings
from shipverse.auth import create_access_token, create_refresh_token,  is_expired, getUserIdByToken
from datetime import timedelta
import datetime
from rest_framework.exceptions import APIException
import stripe
import json
import logging
from smtplib import SMTPException
from .utils import CheckReturnOnBoard
# check authorized


@api_view(['POST'])
def is_jwt_expired(request):
    
    token = request.data['token']
    refreshtoken = request.data['refreshtoken']
    try:
        expired = is_expired(token, refreshtoken)
        return JsonResponse({'data': expired})
    except:
        # If decoding the token fails, it is considered expired
        return JsonResponse({'data': expired})


@api_view(['POST'])
@log_api_activity
def user_create(request):
    try:
        user = Users.objects.get(
            username=request.data['username'], email=request.data['email'])
        return JsonResponse(
            {'result': "username and email address already taken!", 'token': '', 'refreshtoken': ''}, status=status.HTTP_401_UNAUTHORIZED)
    except Users.DoesNotExist:
        user = Users(
            username=request.data['username'], email=request.data['email'])
        user.set_password(request.data['password'])
        user.username = request.data['username']
        user.email = request.data['email']
        user.fullName = request.data['fullName']
        user.phone = request.data['phone']
        user.usertype = request.data['usertype']
        user.parentuser = request.data['parentuser']
        user.roles = request.data['roles']
        user.active = request.data['active']
        user.save()
        # createFreeCheckoutSession(user.id)
        # access_token = create_access_token(user.id, user.username, user.email)
        # refresh_token = create_refresh_token(user.id, user.username, user.email)
        # create email verification token
        if user.parentuser == '0':
            try:
                user.isEmailVerified = False
                user.save()
                result = createEmailToken(request.data['email'])
                if result == True:
                    return JsonResponse({'result': 'Verification email sent successfully'}, status=status.HTTP_200_OK)
            except APIException as e:
                return JsonResponse({'result': str(e.detail)}, status=e.status_code)
        else:
            try:
                result = inviteMailToken(user.username, request.data['email'])
                if result == True:
                    return JsonResponse({'result': 'Create password email sent successfully'}, status=status.HTTP_200_OK)
            except APIException as e:
                return JsonResponse({'result': str(e.detail)}, status=e.status_code)

@log_api_activity
def inviteMailToken(username, email):
    try:
        row = InviteTokens.objects.get(username=username, email=email)
        current_timestamp = datetime.datetime.now().timestamp()
        difference = current_timestamp - row.emailVerificationDate.timestamp()
        if (difference / 60000) < 1:
            raise APIException(
                detail='Invite email sent recently', code='500')
        else:
            current_timestamp = str(int(datetime.datetime.now().timestamp()))
            current_date = datetime.datetime.now().date()
            row.emailInviteToken = current_timestamp
            row.emailInviteDate = current_date
            row.save()
            sent = sendInviteMail(username, email, current_timestamp)
            if sent == 1:
                return True
            else:
                raise APIException(detail='Internal Server Error', code='500')

    except InviteTokens.DoesNotExist:
        current_timestamp = str(int(datetime.datetime.now().timestamp()))
        current_date = datetime.datetime.now().date()
        token = InviteTokens(
            username=username,
            email=email,
            emailInviteToken=current_timestamp,
            emailInviteDate=current_date
        )
        token.save()
        sent = sendInviteMail(username, email, current_timestamp)
        if sent == 1:
            return True
        else:
            raise APIException(detail='Internal Server Error', code='500')

@log_api_activity
def createEmailToken(email):
    try:
        row = VerificationTokens.objects.get(email=email)
        current_timestamp = datetime.datetime.now().timestamp()
        difference = current_timestamp - row.emailVerificationDate.timestamp()
        if (difference / 60000) < 1:
            raise APIException(
                detail='Verification email sent recently', code='500')
        else:
            current_timestamp = str(int(datetime.datetime.now().timestamp()))
            current_date = datetime.datetime.now().date()
            row.emailVerificationToken = current_timestamp
            row.emailVerificationDate = current_date
            row.save()
            sent = sendVerificationEmail(email, current_timestamp)
            if sent == 1:
                return True
            else:
                raise APIException(detail='Internal Server Error', code='500')

    except VerificationTokens.DoesNotExist:
        current_timestamp = str(int(datetime.datetime.now().timestamp()))
        current_date = datetime.datetime.now().date()
        token = VerificationTokens(
            email=email,
            emailVerificationToken=current_timestamp,
            emailVerificationDate=current_date
        )
        token.save()
        sent = sendVerificationEmail(email, current_timestamp)
        if sent == 1:
            return True
        else:
            raise APIException(detail='Internal Server Error', code='500')

@log_api_activity
def sendInviteMail(username, email, token):

    html_ = 'Hi! <br><br> A user account has been created for you at www.app.goshipverse.com.<br>Username:'+username+'<br>Next, create a password at this ' + '<a href="' + \
        settings.FRONTEND_URL + '/setupPassword/' + token + \
            '">link</a>'
    try:
        sent = send_mail(
            'Verify Email',
            '',
            'info@goshipverse.com',
            [email],
            html_message=html_,
            fail_silently=False,
        )
        return sent
    except:
        return ""

@log_api_activity
def sendVerificationEmail(email, token):

    html_ = 'Hi! <br><br> Thanks for your registration<br><br>' + '<a href="' + \
        settings.FRONTEND_URL + '/verify/' + token + \
            '">Click here to activate your account</a>'
    try:
        sent = send_mail(
            'Verify Email',
            '',
            'info@goshipverse.com',
            [email],
            html_message=html_,
            fail_silently=False,
        )
        return sent
    except:
        return ""

@log_api_activity
@api_view(['GET'])
def verifyEmail(request, token):
    try:
        row = VerificationTokens.objects.get(emailVerificationToken=token)
        user = Users.objects.get(email=row.email)
        user.isEmailVerified = True
        user.save()
        row.delete()
        access_token = create_access_token(user.id, user.username, user.email)
        refresh_token = create_refresh_token(
            user.id, user.username, user.email)
        return JsonResponse({'result': 'success', 'token': access_token, 'refreshtoken': refresh_token}, status=status.HTTP_200_OK)
    except VerificationTokens.DoesNotExist:
        return JsonResponse({'result': 'This link is expired'}, status=status.HTTP_403_FORBIDDEN)

@log_api_activity
@api_view(['POST'])
def user_update(request):
    try:
        user = Users.objects.get(username=request.data['username'])
        user.username = request.data['username']
        user.email = request.data['email']
        user.fullName = request.data['fullName']
        user.password = request.data['password']
        user.phone = request.data['phone']
        user.usertype = request.data['usertype']
        user.parentuser = request.data['parentuser']
        user.roles = request.data['roles']
        user.active = request.data['active']
        user.save()
        return JsonResponse(
            {'result': "Success!"}, status=status.HTTP_200_OK)
    except Users.DoesNotExist:

        return JsonResponse(
            {'result': 'Failed'}, status=status.HTTP_401_UNAUTHORIZED)

# signin

@log_api_activity
@api_view(['POST'])
def user_signin(request):
    email = request.data['email']
    # Define a regex pattern for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Check if the email matches the regex pattern
    if re.match(pattern, email):
        user = Users.objects.filter(
            email=request.data['email']).first()
    else:
        user = Users.objects.filter(username=request.data['email']).first()

    if user is None:
        return JsonResponse({'result': 'User not found!'},
                            status=status.HTTP_401_UNAUTHORIZED)
    if not user.check_user_password(request.data['password']):
        return JsonResponse({'result': 'Incorrect password!'},
                            status=status.HTTP_401_UNAUTHORIZED)

    if user.isEmailVerified == False:
        try:
            result = createEmailToken(email)
            if result == True:
                return JsonResponse({'result': 'Verification email sent successfully'}, status=status.HTTP_403_FORBIDDEN)
        except APIException as e:
            return JsonResponse({'result': str(e)}, status=e.status_code)
    if user.parentuser != "0" and user.active == False:
        return JsonResponse({'result': 'Not allowed by owner!'},
                            status=status.HTTP_401_UNAUTHORIZED)

    if (user.parentuser != "0"):
        parentuser = Users.objects.filter(id=user.parentuser).first()
        access_token = create_access_token(
            parentuser.id, user.username, user.email)
        refresh_token = create_refresh_token(
            parentuser.id, user.username, user.email)
    else:
        access_token = create_access_token(
            user.id, user.username, user.email)
        refresh_token = create_refresh_token(
            user.id, user.username, user.email)

    try:
        subuser = Subscriptions.objects.get(userId=user.id)
        count = subuser.subscription_count
    except Subscriptions.DoesNotExist:
        count = 0
    # FromLocation, CarrierUsers, StoreUsers
   
        
    response = JsonResponse(
        {'token': access_token, 'refreshtoken': refresh_token, 'roles': user.roles, 'parentuser': user.parentuser, 'subcount': count,'redirect_onbard' : CheckReturnOnBoard(user.id)})
    return response

# childuser

class CheckReturnOnBoardView(APIView):
    @log_api_activity
    def get(self,requests,formate=None) :
        print('hello world')
        user = Users.objects.all().first()
        
        return Response({"stay_CheckReturnOnBoard" : CheckReturnOnBoard(user.id)},status=status.HTTP_200_OK)

@log_api_activity
@api_view(['POST'])
def getchildaccounts(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)

    try:
        subuser = Subscriptions.objects.get(userId=user_id)
        count = subuser.subscription_count
    except Subscriptions.DoesNotExist:
        count = 0

    account_data = []
    childUsers = Users.objects.filter(parentuser=user_id, active=True)
    count = count * 5
    print(count)
    for childUser in childUsers:
        if count > 0:
            count = count - 1
            continue
        else:
            childUser.active = False
            childUser.save()
    childUsers = Users.objects.filter(parentuser=user_id)
    for childUser in childUsers:
        user_dict = {
            'id': childUser.id,
            'username': childUser.username,
            'fullName': childUser.fullName,
            'email': childUser.email,
            'password': childUser.password,
            'phone': childUser.phone,
            'roles': childUser.roles,
            'parentuser': childUser.parentuser,
            'usertype': childUser.usertype,
            'active': childUser.active,
            # add more fields as needed
        }
        account_data.append(user_dict)
    json_data = json.dumps(account_data)
    return JsonResponse(json_data, safe=False)

@log_api_activity
@api_view(['GET'])
def forgotPassword(request, email):
    try:
        user = Users.objects.get(email=email)
        try:
            result = createForgotPasswordToken(user.email)
            if result == True:
                return JsonResponse({'result': 'Reset password email sent successfully'}, status=status.HTTP_200_OK)
        except APIException as e:
            return JsonResponse({'result': str(e.detail)}, status=e.status_code)
    except Users.DoesNotExist:
        return JsonResponse({'result': "Invalid Email Address"}, status=404)

@log_api_activity
def createForgotPasswordToken(email):
    try:
        token = ResetPasswordTokens.objects.get(email=email)
        current_timestamp = datetime.datetime.now().timestamp()
        difference = current_timestamp - token.newPasswordDate.timestamp()
        if (difference / 60000) < 2:
            raise APIException(
                detail='Reset password email sent recently', code=500)
        else:
            current_timestamp = str(int(datetime.datetime.now().timestamp()))
            current_date = datetime.datetime.now().date()
            token.newPasswordToken = current_timestamp
            token.newPasswordDate = current_date
            token.save()
            sent = sendForgotPasswordEmail(email, current_timestamp)
            if sent == 1:
                return True
            else:
                raise APIException(detail='Internal Server Error', code=500)

    except ResetPasswordTokens.DoesNotExist:
        current_timestamp = str(int(datetime.datetime.now().timestamp()))
        current_date = datetime.datetime.now().date()
        token = ResetPasswordTokens(
            email=email,
            newPasswordToken=current_timestamp,
            newPasswordDate=current_date
        )
        token.save()
        sent = sendForgotPasswordEmail(email, current_timestamp)
        if sent == 1:
            return True
        else:
            raise APIException(detail='Internal Server Error', code='500')

@log_api_activity
def sendForgotPasswordEmail(email, token):

    html_ = 'Hi! <br><br> If you requested to reset your password<br><br>' + '<a href="' + \
        settings.FRONTEND_URL + '/auth/resetpassword/' + token + \
            '">Click here</a>'

    try:
        sent = send_mail(
            'Forgot Password',
            '',
            'info@goshipverse.com',
            [email],
            html_message=html_,
            fail_silently=False,
        )
    except Exception as e:
        raise APIException(
            detail='Reset password email has not been sent', code='500')

    return sent

@log_api_activity
@api_view(['POST'])
def resetPassword(request):

    token = request.data['token']
    row = ResetPasswordTokens.objects.get(newPasswordToken=token)
    user = Users.objects.get(email=row.email)
    user.password = request.data['password']
    user.save()
    return JsonResponse({'result': "Password has been reset successfully"}, status=status.HTTP_200_OK)

@log_api_activity
@api_view(['POST'])
def createCheckoutSession(request):

    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    try:
        user = Users.objects.get(id=user_id)
    except:
        return JsonResponse({'result': "ShipVerse User doesn't exist"}, status=status.HTTP_401_UNAUTHORIZED)
    price = settings.STRIPE_PRICE_ID
    count = request.data['count']
    domain_url = settings.FRONTEND_URL
    stripe.api_key = settings.STRIPE_API_KEY
    try:
        subuser = Subscriptions.objects.get(userId=user_id)
    except Subscriptions.DoesNotExist:
        subuser = Subscriptions(userId=user_id)
    print(price)
    subuser.save()
    if subuser.subscription_id == "":
        try:
            # Create new Checkout Session for the order
            # Other optional params include:
            # [billing_address_collection] - to display billing address details on the page
            # [customer] - if you have an existing Stripe Customer ID
            # [customer_email] - lets you prefill the email input in the form
            # [automatic_tax] - to automatically calculate sales tax, VAT and GST in the checkout page
            # For full details see https://stripe.com/docs/api/checkout/sessions/create

            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url +
                '/application/settings/payment?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + '/application/settings/payment',
                mode='subscription',
                customer_email=user.email,  # Here

                # automatic_tax={'enabled': True},
                line_items=[{
                    'price': price,
                    'quantity': count
                }],
                client_reference_id=user_id
            )
            # return redirect(checkout_session.url)
            print(checkout_session)
            return JsonResponse({'result': checkout_session.url}, status=200)

        except Exception as e:
            print({'result': str(e)})
            return JsonResponse({'result': str(e)}, status=500)
    else:
        print("------------------------")
        subscriptions = stripe.Subscription.list(customer=subuser.customer_id)
        try:
            items = subscriptions['data'][0]['items']['data']
            print(items)
            for item in items:
                item['quantity'] = count
            stripe.Subscription.modify(
                subscriptions['data'][0]['id'],
                items=[{"id": items[0]['id'],
                       "price": price, "quantity": count}],
            )
            return JsonResponse({'result': "changed", 'count': count}, status=200)
        except Exception as e:
            print({'result': e})
            return JsonResponse({'result': "failed"}, status=500)

@log_api_activity
@api_view(['POST'])
def webhook_received(request):
    stripe.api_key = settings.STRIPE_API_KEY
    webhook_secret = settings.WEBHOOK_SECRET
    # webhook_secret = 'whsec_39273f9309a344d009c3abfa7d5e5abd1feb91ec18bf507f4847f3d171c19d46'

    request_data = request.body
    event = None
    event_type = None
    data = None
    print(webhook_secret)
    if webhook_secret:

        signature = request.headers.get('stripe-signature')

        try:
            event = stripe.Webhook.construct_event(
                payload=request_data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except ValueError as e:
            # Invalid payload
            print("invalid payload")
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            print("invalid signature")
            raise e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
        data = data['object']

    if event_type == 'payment_intent.succeeded':
        print("--------Payment.intent.succeeded")
        print(data)
        customer = data['object'].customer
        try:
            subuser = Subscriptions.objects.filter(
                customer_id=customer).first()
        except Subscriptions.DoesNotExist:
            return JsonResponse({'status': 'failed'})
        subuser.result = event_type
        subuser.save()
        # Payment is successful and the subscription is created.
        # You should provision the subscription and save the customer ID to your database.
    elif event_type == 'customer.subscription.updated':
        print("-------------customer.subscription.updated")
        print(data)
        try:
            subuser = Subscriptions.objects.filter(
                customer_id=data['object']['customer']).first()
        except Subscriptions.DoesNotExist:
            return JsonResponse({'status': 'failed'})

        amount = data['object'].quantity
        if data['object'].canceled_at is None:
            subuser.cancel_date = None
        else:
            subuser.cancel_date = datetime.datetime.fromtimestamp(
                data['object'].canceled_at)

        users = Users.objects.filter(parentuser=subuser.userId, active=True)
        # Get the first 'count' users to remove
        users_to_remove = users[amount*5:]
        # users_to_remove = users[:amount*5]
        # Perform any necessary operations with the users to remove

        # Delete the users from the database
        for user in users_to_remove:
            user.active = False
            user.save()
        subuser.subscription_count = amount
        subuser.result = event_type
        subuser.save()
    elif event_type == 'checkout.session.completed':
        print("---------------Checkout.session.completed")
        print(data)
        userId = data['object'].client_reference_id

        try:
            subuser = Subscriptions.objects.filter(userId=userId).first()
        except Subscriptions.DoesNotExist:
            subuser = Subscriptions(userId=userId)
        subuser.userId = userId
        subuser.customer_id = data['object'].customer
        subuser.subscription_id = data['object'].subscription

        # subuser.start_date = datetime.datetime.now().date()
        subuser.result = event_type
        subuser.save()
    elif event_type == 'invoice.paid':
        # Continue to provision the subscription as payments continue to be made.
        # Store the status in your database and check when a user accesses your service.
        # This approach helps you avoid hitting rate limits.
        print('invoice.paid')
        print(data)
        customer_email = data['object'].customer_email
        try:
            user = Users.objects.get(email=customer_email)
        except:
            return JsonResponse({'result': "ShipVerse User doesn't exist"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            subuser = Subscriptions.objects.filter(
                userID=user.id).first()
        except Subscriptions.DoesNotExist:
            subuser = Subscriptions(userId=user.id)
        subuser.userId = user.id
        subuser.customer_id = data['object'].customer
        subuser.subscription_id = data['object'].subscription
        subuser.start_date = datetime.datetime.now().date()
        subuser.result = event_type
        subuser.save()
        # print(event_type)
        # print(data['object'])
    elif event_type == 'invoice.payment_failed':
        # The payment failed or the customer does not have a valid payment method.
        # The subscription becomes past_due. Notify your customer and send them to the
        # customer portal to update their payment information.
        print("--------------------", "invoice.payment.failed")
        print(data)
        try:
            subuser = Subscriptions.objects.filter(
                customer_id=data['object'].customer).first()
        except Subscriptions.DoesNotExist:
            return JsonResponse({'status': 'failed'})
        subuser.result = event_type
        subuser.save()
        # print(event_type)
        # print(data['object'])
    elif event_type == 'invoice.payment_succeeded':
        print("--------------------", "invoice.payment_succeeded")
        customer_email = data['object'].customer_email
        print(customer_email)
        try:
            user = Users.objects.filter(email=customer_email).first()
        except:
            return JsonResponse({'result': "ShipVerse User doesn't exist"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            subuser = Subscriptions.objects.filter(
                userId=user.id).first()
        except Subscriptions.DoesNotExist:
            subuser = Subscriptions(userId=user.id)
        print(subuser)
        amount = data['object'].lines.data[0].quantity
        subuser.start_date = datetime.datetime.fromtimestamp(
            data['object'].lines.data[0].period.end)
        subuser.end_date = datetime.datetime.fromtimestamp(
            data['object'].lines.data[0].period.end)
        subuser.subscription_count = amount
        subuser.result = event_type
        subuser.save()
        # print(event_type)
        # print(data['object'])
    elif event_type == 'customer.subscription.deleted':
        try:
            subuser = Subscriptions.objects.filter(
                customer_id=data['object'].customer).first()
        except Subscriptions.DoesNotExist:
            return JsonResponse({'status': 'failed'})
        subuser.delete()
    else:
        print('Unhandled event type {}'.format(event_type))

    return JsonResponse({'status': 'success'})

@log_api_activity
@api_view(['POST'])
def cancel_subscription(request):

    stripe.api_key = settings.STRIPE_API_KEY
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    isCancel = request.data['isCancel']
    try:
        subuser = Subscriptions.objects.get(userId=user_id)
    except Subscriptions.DoesNotExist:
        return JsonResponse({'result': 'failed'}, status=500)
    stripe.Subscription.modify(
        subuser.subscription_id, cancel_at_period_end=isCancel,)
    return JsonResponse({'result': 'success', 'count': 0}, status=200)

@log_api_activity
@api_view(['POST'])
def getSubscriptions(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    user = Users.objects.get(id=user_id)
    try:
        subuser = Subscriptions.objects.get(userId=user_id)
    except Subscriptions.DoesNotExist:
        return JsonResponse({'result': 'success', 'count': 0, 'user_created': user.date_created}, status=200)
    if subuser.start_date is None:
        date_value = ""  # Set an empty string if start_date is None
    else:
        date_value = subuser.start_date.date()  # Convert start_date to a date object
    if subuser.end_date is None:
        end_date = ""  # Set an empty string if end_date is None
    else:
        end_date = subuser.end_date.date()  # Convert end_date to a date object
    if subuser.cancel_date is None:
        cancel_date = ""  # Set an empty string if cancel_date is None
    else:
        # Convert cancel_date to a date object
        cancel_date = subuser.cancel_date.date()

    # Create the JSON response
    response_data = {
        'result': 'success',
        'count': subuser.subscription_count,
        'start_date': date_value,
        'end_date': end_date,
        'cancel_date': cancel_date,
        'user_created': user.date_created
    }

    # Return the JSON response with a 200 status code
    return JsonResponse(response_data, status=200)

@log_api_activity
@api_view(['POST'])
def resetInvitePassword(request):

    token = request.data['token']
    row = InviteTokens.objects.get(emailInviteToken=token)
    user = Users.objects.get(username=row.username, email=row.email)
    user.password = request.data['password']
    user.save()
    return JsonResponse({'result': "Password has been reset successfully"}, status=status.HTTP_200_OK)

@log_api_activity
def my_cron_job():
    logging.basicConfig(
        filename='/var/www/shipverse/cron.log', level=logging.INFO)
    logging.info("Cron job executed successfully")
    fourteen_days_ago = datetime.now() - timedelta(days=14)
    users = Users.objects.filter(date_created=fourteen_days_ago)
    for user in users:
        logging.info(user.username)
        try:
            subuser = Subscriptions.objects.get(userId=user.id)
        except Subscriptions.DoesNotExist:
            html_ = 'Hi! <br><br> Trial period has been ended up.<br>Username:' + user.username + '<br>Please update subscription ' + '<a href="' + \
                settings.FRONTEND_URL + '/application/settings/payment' + '">link</a>'
            try:
                sent = send_mail(
                    'Verify Email',
                    '',
                    'info@goshipverse.com',
                    [user.email],
                    html_message=html_,
                    fail_silently=False,
                )
                return sent
            except SMTPException as e:
                logging.info('There was an error sending an email: ', e)

def add_carrier_user(user, data):
    return UserCarrier.objects.create(
        user = user,
        carrier = data['carrier'],
        fullName = data['fullname'],
        company_name = data['company_name'],
        email = data['email'],
        phone = int(data['phone']),
        street1 = data['street1'],
        street2 = data['street2'],
        city = data['city'],
        state = data['state'],
        zip_code = int(data['zip_code']),
        account_nickname = data['account_nickname'],
        account_number = data['account_number'],
        country = data["country"],
        postcode = int(data['postcode'])
    )
        
class UPS_users_account_details(APIView):

    def post(self,request) :
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        user_id = getUserIdByToken(auth_header)
        user = Users.objects.get(id=user_id)
        if not user : 
            return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
        
        if(request.data['carrier']):
            url = "https://ct.soa-gw.canadapost.ca/ot/token"
            cred = base64.b64encode(str(settings.CANADAPOST_USERNAME + ":" + settings.CANADAPOST_PASSWORD).encode("ascii"))
            result = requests.post(url=url,data=None,headers={
                "Accept":"application/vnd.cpc.registration-v2+xml",
                "Content-Type":"application/vnd.cpc.registration-v2+xml",
                "Authorization":"Basic "+ cred.decode("ascii"),
                "Accept-language":"en-CA"
            })
            json_decoded = xmltodict.parse(result.content)
            redirect_url = "https://www.canadapost-postescanada.ca/information/app/drc/testMerchant"
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

@api_view(['POST'])
def verify_canadapost_registration(request):
    token_id = request.data["tokenId"]
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    user_id = getUserIdByToken(auth_header)
    user = Users.objects.get(id=user_id)
    if not user : 
        return Response({"message": "User not found or Unauthorized !"},status=status.HTTP_200_OK)
    
    url = "https://ct.soa-gw.canadapost.ca/ot/token/"+token_id
    cred = base64.b64encode(str(settings.CANADAPOST_USERNAME + ":" + settings.CANADAPOST_PASSWORD).encode("ascii"))
    result = requests.post(url=url,data=None,headers={
        "Accept":"application/vnd.cpc.registration-v2+xml",
        "Content-Type":"application/vnd.cpc.registration-v2+xml",
        "Authorization":"Basic "+ cred.decode("ascii"),
        "Accept-language":"en-CA"
    })
    json_decoded = xmltodict.parse(result.content)
    if(result.status_code == 200):
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

