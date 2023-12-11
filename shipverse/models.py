from django.db import models
from django.utils import timezone
# Create your models here.
from django.contrib.auth.hashers import make_password, check_password


class Users(models.Model):
    username = models.CharField(
        max_length=70, blank=False, default='', unique=True)
    fullName = models.CharField(max_length=70, null=True)
    email = models.EmailField(max_length=70, null=True)
    password = models.CharField(max_length=500, null=True)
    phone = models.CharField(max_length=70, null=True)
    usertype = models.CharField(max_length=70, null=True)
    roles = models.CharField(max_length=70, null=True)
    parentuser = models.CharField(max_length=70, null=True)
    customerId = models.CharField(max_length=70, null=True)
    active = models.BooleanField(default=False)
    isEmailVerified = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now=True)
    
    def set_password(self, password):
        self.password = make_password(password)
    
    def check_user_password(self, raw_password):
        return check_password(raw_password,self.password)

    def __str__(self) -> str:
        return self.username


class VerificationTokens(models.Model):
    # username = models.CharField(max_length=70, blank=False, unique=True)
    email = models.EmailField(max_length=70, blank=False, unique=True)
    emailVerificationToken = models.CharField(
        max_length=70, blank=True, null=True)
    emailVerificationDate = models.DateTimeField(blank=True, null=True)


class ResetPasswordTokens(models.Model):
    email = models.EmailField(max_length=70, blank=False, unique=True)
    newPasswordToken = models.CharField(max_length=70, blank=True, null=True)
    newPasswordDate = models.DateTimeField(blank=True, null=True)


class InviteTokens(models.Model):
    username = models.CharField(max_length=70, blank=False, unique=True)
    email = models.EmailField(max_length=70, blank=False, unique=True)
    emailInviteToken = models.CharField(
        max_length=70, blank=True, null=True)
    emailInviteDate = models.DateTimeField(blank=True, null=True)


class Packages(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    packageName = models.CharField(max_length=70, blank=False, default='')
    measureUnit = models.CharField(max_length=10, blank=True, default='')
    length = models.FloatField(blank=False, default='0')
    width = models.FloatField(blank=False, default='0')
    height = models.FloatField(blank=False, default='0')
    packageCode = models.CharField(max_length=70, blank=True, default='')
    upsPackage = models.BooleanField(default=False)


class StoreUsers(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    access_token = models.CharField(max_length=255, default='', null=True)
    storeHash = models.CharField(max_length=255, default='', null=True)
    code = models.CharField(max_length=255, default='', null=True)
    accessScope = models.CharField(max_length=255, default='', null=True)
    isAdmin = models.BooleanField(default=False)


class CarrierUsers(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    accountNumber = models.CharField(max_length=70, blank=False, default='')
    status = models.CharField(max_length=70, default='')
    access_token = models.CharField(max_length=2048, default='')
    refresh_token = models.CharField(max_length=512, default='')


class FromLocation(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    locationName = models.CharField(max_length=70, blank=True, default='')
    fullName = models.CharField(max_length=70, blank=True, default='')
    attentionName = models.CharField(max_length=70, blank=True, default='')
    phone = models.CharField(max_length=70, blank=True, default='')
    address = models.CharField(max_length=70, blank=True, default='')
    address1 = models.CharField(max_length=70, blank=True, default='')
    city = models.CharField(max_length=70, blank=True, default='')
    stateCode = models.CharField(max_length=10, blank=True, default='')
    postalCode = models.CharField(max_length=10, blank=True, default='')
    countryCode = models.CharField(max_length=10, blank=True, default='')
    email = models.EmailField(max_length=70, blank=True, default='')
    timezone = models.CharField(max_length=70, blank=True, default='')
    selected = models.BooleanField(default=False)
    residential = models.BooleanField(default=False)
    returnFullName = models.CharField(max_length=70, blank=True, default='')
    returnAttentionName = models.CharField(
        max_length=70, blank=True, default='')
    returnPhone = models.CharField(max_length=70, blank=True, default='')
    returnAddress = models.CharField(max_length=70, blank=True, default='')
    returnAddress1 = models.CharField(max_length=70, blank=True, default='')
    returnCity = models.CharField(max_length=70, blank=True, default='')
    returnStateCode = models.CharField(max_length=10, blank=True, default='')
    returnPostalCode = models.CharField(max_length=10, blank=True, default='')
    returnCountryCode = models.CharField(
        max_length=10, blank=True, default='')
    returnEmail = models.EmailField(max_length=70, blank=True, default='')
    returnTimezone = models.CharField(max_length=70, blank=True, default='')


class ShipperLocation(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    locationName = models.CharField(max_length=70, blank=True, default='')
    fullName = models.CharField(max_length=70, blank=True, default='')
    attentionname = models.CharField(max_length=70, blank=True, default='')
    taxidnum = models.CharField(max_length=70, blank=True, default='')
    phone = models.CharField(max_length=70, blank=True, default='')
    shipperno = models.CharField(max_length=70, blank=True, default='')
    fax = models.CharField(max_length=70, blank=True, default='')
    address = models.CharField(max_length=70, blank=True, default='')
    address1 = models.CharField(max_length=70, blank=True, default='')
    city = models.CharField(max_length=70, blank=True, default='')
    statecode = models.CharField(max_length=10, blank=True, default='')
    postalcode = models.CharField(max_length=10, blank=True, default='')
    countrycode = models.CharField(max_length=2, blank=True, default='')
    email = models.CharField(max_length=30, blank=True, default='')
    selected = models.BooleanField(default=True)


class Shipment(models.Model):
    userId = models.CharField(max_length=20, blank=False, default='')
    order = models.CharField(max_length=20, blank=True, default='')
    accountNumber = models.CharField(max_length=30, blank=True, default='')
    carrier = models.CharField(max_length=30, blank=True, default='')
    trackingnumber = models.CharField(max_length=30, blank=True, default='')
    image = models.TextField(max_length=1024*1024, null=True)
    invoice = models.TextField(max_length=1024*1024, null=True)
    trackingurl = models.CharField(max_length=256, blank=True, default='')
    datecreated = models.DateTimeField(auto_now=True)


class InternationalSettings(models.Model):
    userId = models.CharField(max_length=20, blank=False, default='')
    defaultContentType = models.CharField(blank=True, default="")
    termsOfSale = models.CharField(blank=True, default="")
    declarationStatement = models.CharField(blank=True, default="")


class Taxes(models.Model):
    userId = models.CharField(max_length=20, blank=False, default='')
    idType = models.CharField(max_length=10, blank=True, default=0)
    authority = models.CharField(max_length=2, blank=True, default='')
    number = models.CharField(max_length=70, blank=True, default='')
    nickname = models.CharField(max_length=70, blank=True, default='')
    description = models.CharField(max_length=70, blank=True, default='')


class Subscriptions(models.Model):
    userId = models.CharField(max_length=70, blank=False, default='')
    subscription_count = models.IntegerField(default=0)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    cancel_date = models.DateTimeField(blank=True, null=True)
    customer_id = models.CharField(max_length=70, blank=True, default='')
    subscription_id = models.CharField(max_length=70, default='')
    result = models.CharField(max_length=70, blank=True, default='')


class Shop(models.Model):
    userId = models.CharField(max_length=20, blank=False, default='')
    shopify_domain = models.CharField(max_length=255)
    shopify_token = models.CharField(max_length=255)
    access_scopes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserCarrier(models.Model):
    user = models.ForeignKey(Users,on_delete=models.CASCADE)
    carrier = models.CharField(max_length=20)
    fullName = models.CharField(max_length=250)
    company_name = models.CharField(max_length=250)
    email = models.EmailField()
    phone = models.BigIntegerField()
    street1 = models.CharField(max_length=250)
    street2 = models.CharField(max_length=250,blank=True,null=True)
    city = models.CharField(max_length=250)
    state  = models.CharField(max_length=250)
    country1 = models.CharField(max_length=250)
    zip_code = models.IntegerField()
    account_number = models.CharField(max_length=250)
    account_nickname = models.CharField(max_length=250,blank=True,null=True)
    country = models.CharField(max_length=20)
    postcode = models.IntegerField()


class CandapostUserDetails(models.Model):
    customer_number = models.CharField(max_length=250, null=True)
    contract_number = models.CharField(max_length=250, null=True)
    merchant_username = models.CharField(max_length=250, null=True)
    merchant_password = models.CharField(max_length=250, null=True)
    has_credit_card = models.CharField(max_length=250, null=True)

    def __str__(self) -> str:
        return self.customer_number