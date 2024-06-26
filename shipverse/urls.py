# Create your views here.
from django.urls import path, re_path
from . import views
from . import bigcommerceviews
from . import upsviews
from . import shopifyviews
from . import canadapost_views

urlpatterns = [
    re_path(r'^api/users/signin$', views.user_signin),
    re_path(r'^api/users/signup$', views.user_create),
    re_path(r'^api/users/update$', views.user_update),
    
    path('api/users/verify/<str:token>/', views.verifyEmail),
    path('api/users/forgotpassword/<str:email>/', views.forgotPassword),
    path('api/users/existforegettoken/<str:token>/',views.existforgettoken),
    re_path(r'^api/users/is_jwt_expired$', views.is_jwt_expired),
    re_path(r'^api/users/getchildaccounts$', views.getchildaccounts),
    path('api/users/resetpassword', views.resetPassword),
    path('api/users/resetinvitepassword', views.resetInvitePassword),

    # payment
    path('api/payment/create_checkout_session', views.createCheckoutSession),
    path('api/payment/get_subscriptions', views.getSubscriptions),
    path('webhook', views.webhook_received),
    path('api/payment/cancel_subscription', views.cancel_subscription),

    # shopify
    path('api/shopify/getToken', shopifyviews.getToken),
    path('api/shopify/getShopifyStores', shopifyviews.getShopifyStores),
    path('api/shopify/getshopifyorders', shopifyviews.getOrders),
    path('api/shopify/update2shipment', shopifyviews.update2shipment),
    path('api/shopify/markasshipped', shopifyviews.markasshipped),
    path('api/shopify/removestore', shopifyviews.removestore),
    path('api/shopify/addshopifystore', shopifyviews.addshopifystore),
    # bigcommerce
    re_path(r'^api/bigcommerce/getbigcommerceorders$',
            bigcommerceviews.get_orders),
    re_path(r'^api/bigcommerce/isAuth$', bigcommerceviews.get_isAuth),
    re_path(r'^api/bigcommerce/disconnect$', bigcommerceviews.disconnect),
    re_path(r'^api/bigcommerce/update2shipment$',
            bigcommerceviews.update2shipment),
    re_path(r'^api/bigcommerce/markasshipped$',
            bigcommerceviews.markasshipped),
    re_path(r'^api/bigcommerce/getBigCommerceStores$',
            bigcommerceviews.getBigCommerceStores),
    re_path(r'^api/bigcommerce/getProducts$',
            bigcommerceviews.getProducts),
    re_path(r'^api/bigcommerce/saveUserId$', bigcommerceviews.saveUserId),
    re_path(r'^api/bigcommerce/add',
            bigcommerceviews.addBigCommerceStore),
    re_path(r'^api/bigcommerce/load',
            bigcommerceviews.loadBigCommerceStore),
    re_path(r'^api/bigcommerce/uninstall',
            bigcommerceviews.uninstallBigCommerceStore),

#   UPS APIS

    re_path(r'^api/ups/validate$', upsviews.validate),
    re_path(r'^api/ups/getToken$', upsviews.getToken),
    re_path(r'^api/ups/refreshToken$', upsviews.refreshToken),
    re_path(r'^api/ups/isUPSAuth$', upsviews.isUPSAuth),
    re_path(r'^api/ups/disconnect$', upsviews.disconnect),
    re_path(r'^api/ups/createLabel$', upsviews.createLabel),
    re_path(r'^api/ups/getLabel$', upsviews.getLabel),
    re_path(r'^api/ups/getInvoice$', upsviews.getInvoice),
    re_path(r'^api/ups/getOrderRate$',
            upsviews.authenticate_and_refresh_token(upsviews.getOrderRate)),
    re_path(r'^api/ups/getOrderRates$', upsviews.getOrderRates),
    re_path(r'^api/ups/getRateServices$', upsviews.getRateServices),
    re_path(r'^api/ups/addFromLocation$', upsviews.addFromLocation),
    re_path(r'^api/ups/updateFromLocation$', upsviews.updateFromLocation),
    re_path(r'^api/ups/deleteFromLocation$', upsviews.deleteFromLocation),
    re_path(r'^api/ups/getFromLocations$', upsviews.getFromLocations),
    re_path(r'^api/ups/checkAddressValidation$',
            upsviews.checkAddressValidation),
    re_path(r'^api/ups/addUser$',
            upsviews.addUser),
    re_path(r'^api/ups/getUsers$', upsviews.getUsers),
    re_path(r'^api/ups/removeUser$', upsviews.removeUser),
    re_path(r'^api/ups/addPackage$', upsviews.addPackage),
    re_path(r'^api/ups/updatePackage$', upsviews.updatePackage),
    re_path(r'^api/ups/getPackages$', upsviews.getPackages),
    re_path(r'^api/ups/removePackage$', upsviews.removePackage),
    re_path(r'^api/ups/makeDefaultUser$', upsviews.makeDefaultUser),
    re_path(r'^api/ups/addTax$', upsviews.addTax),
    re_path(r'^api/ups/getTaxes$', upsviews.getTaxes),
    re_path(r'^api/ups/deleteTax$', upsviews.deleteTax),
    re_path(r'^api/ups/saveInternationalSettings$',
            upsviews.saveInternationalSettings),
    re_path(r'^api/ups/getInternationalSettings$',
            upsviews.getInternationalSettings),
    re_path(r'^api/ups/getAddress$',
            upsviews.getAddress),
    re_path(r'^api/ups/addressValidation$',
            upsviews.addressValidation),


    re_path(r'^api/shopify/customers/data_request$',
            shopifyviews.data_request_webhook),
    re_path(r'^api/shopify/customers/redact$',
            shopifyviews.customer_redact_webhook),
    re_path(r'^api/shopify/shop/redact$', shopifyviews.shop_redact_webhook),
    #     re_path(r'^api/ups/labelRecovery$',
    #             upsviews.labelRecovery),
    
    re_path(r'^application/settings/CheckReturnOnBoard$', views.CheckReturnOnBoardView.as_view()),

    # CANADAPOST

    re_path(r'^api/canadapost/addCarrier', canadapost_views.CanadaUsersAccountDetails.as_view()),
    re_path(r'^api/canadapost/verifyCP', canadapost_views.VerifyCanadaPost.as_view()),
    re_path(r'^api/canadapost/createLabel', canadapost_views.ShipmentCreateAPI.as_view()),
    re_path(r'^api/canadapost/getRates', canadapost_views.CanadaPostPrice.as_view()),
    re_path(r'^api/canadapost/getArtifact', canadapost_views.GetArtifactAPI.as_view()),


]