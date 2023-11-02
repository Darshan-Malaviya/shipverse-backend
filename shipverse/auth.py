from rest_framework.exceptions import AuthenticationFailed
import jwt
from jwt.exceptions import ExpiredSignatureError
from rest_framework.parsers import JSONParser
import datetime
ACCESS_TOKEN_SECRET = 'Access_secret_string_12345'
REFRESH_TOKEN_SECRET = 'Refresh_secret_string_12345'


def create_access_token(id, username, email):
    return jwt.encode({
        'user_id': id,
        'username': username,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow()
    }, ACCESS_TOKEN_SECRET, algorithm='HS256')


def decode_access_token(token):
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=['HS256'])
        return {'user_id': payload['user_id'], 'username': payload['username'], 'email': payload['email']}
    except ExpiredSignatureError:
        return {'user_id': "", 'username': "", 'email': ""}


def create_refresh_token(id, username, email):
    return jwt.encode({
        'user_id': id,
        'username': username,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=2),
        'iat': datetime.datetime.utcnow()
    }, REFRESH_TOKEN_SECRET, algorithm='HS256')


def decode_refresh_token(token):
    try:
        payload = jwt.decode(token, REFRESH_TOKEN_SECRET, algorithms='HS256')
        return {'user_id': payload['user_id'], 'username': payload['username'], 'email': payload['email']}
    except:
        return {'user_id': "", 'username': "", 'email': ""}


def is_expired(token, refreshtoken):
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=['HS256'])
        return {'expired': False, 'token': token, 'refreshtoken': refreshtoken}
    except ExpiredSignatureError:
        try:
            payload = jwt.decode(
                refreshtoken, REFRESH_TOKEN_SECRET, algorithms=['HS256'])
            token = create_access_token(
                payload['user_id'], payload['username'], payload['email'])
            refreshtoken = create_refresh_token(
                payload['user_id'], payload['username'], payload['email'])
            return {'expired': False, 'token': token, 'refreshtoken': refreshtoken}
        except ExpiredSignatureError:
            # Refresh Token is expired
            return {'expired': True, 'token': '', 'refreshtoken': ''}
        except:
            # Refresh Token is invalid or other error occurred
            return {'expired': True, 'token': '', 'refreshtoken': ''}
    except:
        # Token is invalid or other error occurred
        return {'expired': True, 'token': '', 'refreshtoken': ''}


def getUserIdByToken(token):

    token_data = decode_access_token(token)
    if 'user_id' in token_data:
        user_id = token_data['user_id']
        return user_id  # user_id exists in token_data
    else:
        return {user_id: ""}  # user_id does not exist in token_data


def createResetToken(id,  email):
    return jwt.encode({
        'user_id': id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        'iat': datetime.datetime.utcnow()
    }, ACCESS_TOKEN_SECRET, algorithm='HS256')


def decodeResetToken(token):
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=['HS256'])
        return {'user_id': payload['user_id'], 'email': payload['email']}
    except ExpiredSignatureError:
        return {'user_id': "", 'email': ""}
