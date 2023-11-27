
from .auth import getUserIdByToken
from .models import *

def CheckReturnOnBoard(user_id : str):

    if StoreUsers.objects.filter(userId=f"{user_id}").count() == 0 or CarrierUsers.objects.filter(userId=f"{user_id}").count() == 0 or FromLocation.objects.filter(userId=f"{user_id}").count() == 0 :
        return False
    else: return True