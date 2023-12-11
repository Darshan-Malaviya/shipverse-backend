from django.contrib import admin
from .models import Users, VerificationTokens, ResetPasswordTokens, InviteTokens, Packages, \
    StoreUsers, CarrierUsers, FromLocation, ShipperLocation, Shipment, InternationalSettings, \
    Taxes, Subscriptions, Shop, UserCarrier, CandapostUserDetails


admin.site.register(Users)
admin.site.register(VerificationTokens)
admin.site.register(ResetPasswordTokens)
admin.site.register(InviteTokens)
admin.site.register(Packages)
admin.site.register(StoreUsers)
admin.site.register(CarrierUsers)
admin.site.register(FromLocation)
admin.site.register(ShipperLocation)
admin.site.register(Shipment)
admin.site.register(InternationalSettings)
admin.site.register(Taxes)
admin.site.register(Subscriptions)
admin.site.register(Shop)
admin.site.register(UserCarrier)
admin.site.register(CandapostUserDetails)