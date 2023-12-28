import os
import base64

if not os.environ["IS_PROD"]:
    canadaPost = os.environ.get("canadapost_prod")
    canadapost_uname = os.environ.get("canadapost_username")
    canadapost_pass = os.environ.get("canadapost_password") 

else:
    canadaPost = os.environ.get("canadapost_dev")
    canadapost_uname = os.environ.get("canadapost_username_debug")
    canadapost_pass = os.environ.get("canadapost_password_debug")   
   
xmlns="http://www.canadapost.ca/ws/shipment-v8"
cpVerify_link = "https://dev1.goshipverse.com/cpVerify"
acceptLanguage = "en-CA"
contentTypeRegistrationXml = "application/vnd.cpc.registration-v2+xml"
contentTypeShipRateXml = "application/vnd.cpc.ship.rate-v4+xml"

encoded_cred = base64.b64encode(str(canadapost_uname + ":" + canadapost_pass).encode("ascii")).decode("ascii")

customerNo = os.environ.get("customer_number")