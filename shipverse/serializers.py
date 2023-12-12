from rest_framework import serializers
from shipverse.models import Users,  StoreUsers, CarrierUsers, FromLocation, Shipment, ShipperLocation, InternationalSettings, Taxes, UserCarrier
from django.core.validators import MaxValueValidator, MinValueValidator


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = '__all__'


class StoreUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreUsers
        fields = '__all__'


class CarrierUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarrierUsers
        fields = '__all__'


class FromLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FromLocation
        fields = '__all__'


class ShipperLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipperLocation
        fields = '__all__'


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = '__all__'


class InternationalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternationalSettings
        fields = '__all__'


class TaxesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Taxes
        fields = '__all__'


class UPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCarrier
        fields = '__all__'


class UserCarrierSerializer(serializers.Serializer):

    carrier = serializers.CharField(required = True)
    fullName = serializers.CharField(required = True)
    company_name = serializers.CharField(required = True)
    email = serializers.EmailField(required = True)
    phone = serializers.IntegerField(required = True,
                                     validators=[
                    MinValueValidator(-9223372036854775808),  # Minimum value for a 64-bit signed integer
                    MaxValueValidator(9223372036854775807),   # Maximum value for a 64-bit signed integer
                ]
            )
    street1 = serializers.CharField(required = True)
    street2 = serializers.CharField(required = True)
    city = serializers.CharField(required = True)
    state = serializers.CharField(required = True)
    country1 = serializers.CharField(required = True)
    zip_code = serializers.CharField(required = True)
    account_number = serializers.CharField(required = True)
    account_nickname = serializers.CharField(required = True)
    country = serializers.CharField(required = True)
    postcode = serializers.CharField(required = True)