from rest_framework import serializers
from shipverse.models import Users,  StoreUsers, CarrierUsers, FromLocation, Shipment, ShipperLocation, InternationalSettings, Taxes


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
