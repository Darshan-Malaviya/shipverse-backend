from django.contrib import admin
from .views import Users, VerificationTokens, ResetPasswordTokens, InviteTokens

admin.site.register(Users)
admin.site.register(VerificationTokens)
admin.site.register(ResetPasswordTokens)
admin.site.register(InviteTokens)