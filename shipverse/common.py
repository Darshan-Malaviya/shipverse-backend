from django.core.mail import send_mail
from django.core import mail
from dotenv import load_dotenv
import os
from shipverse.models import Users, VerificationTokens, ResetPasswordTokens, InviteTokens, Subscriptions
from  django.conf import settings
import datetime
from rest_framework.exceptions import APIException
import logging
from datetime import timedelta
from smtplib import SMTPException
from .models import UserCarrier


def send_email(subject, message, recipient_list):

    from_email = os.environ.get("EMAIL_HOST_USER")
    
    return send_mail(subject, message, from_email, recipient_list, html_message=message)


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
        print("verification token")
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


def sendInviteMail(username, email, token):
    html_ = 'Hi! <br><br> A user account has been created for you at www.app.goshipverse.com.<br>Username:'+username+'<br>Next, create a password at this ' + '<a href="' + \
        settings.FRONTEND_URL + '/setupPassword/' + token + \
            '">link</a>'
    try:
        send_email(subject="Verification Mail",
                   message=html_,
                   recipient_list=[email])
        
        return 1
    except Exception as e:
        print(e)
        return ""


def sendVerificationEmail(email, token):

    html_ = 'Hi! <br><br> Thanks for your registration<br><br>' + '<a href="' + \
        settings.FRONTEND_URL + '/verify/' + token + \
            '">Click here to activate your account</a>'
    try:
        # sent = send_mail(
        #     'Verify Email',
        #     '',
        #     'info@goshipverse.com',
        #     [email],
        #     html_message=html_,
        #     fail_silently=False,
        # )

        send_email(subject="Verify Email",
                   message=html_,
                   recipient_list=[email])
        return 1
    except:
        return ""


def inviteMailToken(username, email):
    try:
        row = InviteTokens.objects.get(username=username, email=email)
        print("invite -> ", row)
        current_timestamp = datetime.datetime.now().timestamp()
        difference = current_timestamp - row.emailInviteDate.timestamp()
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


def sendForgotPasswordEmail(email, token):

    html_ = 'Hi! <br><br> If you requested to reset your password<br><br>' + '<a href="' + \
        settings.FRONTEND_URL + '/auth/resetpassword/' + token + \
            '">Click here</a>'

    try:
        send_email(subject="Forgot Password",
                   message=html_,
                   recipient_list=[email])
        
        sent = 1
    except Exception as e:
        raise APIException(
            detail='Reset password email has not been sent', code='500')

    return sent


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
                # sent = send_mail(
                #     'Verify Email',
                #     '',
                #     'info@goshipverse.com',
                #     [user.email],
                #     html_message=html_,
                #     fail_silently=False,
                # )
                send_email(subject="Verify Email",
                           message=html_,
                           recipient_list=[user.email])
                return 1
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