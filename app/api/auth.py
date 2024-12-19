import sqlalchemy as sa
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app import db
from app.models import User
from app.api.errors import error_response

# Note: to integrate with Flask-HTTPAuth, the applications needs to provide 2 functions:
# 1. Check the username and password provided by the user (verify)
# 2. Return the error response in the case of an authentication failire (error handler)

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

@basic_auth.verify_password
def verify_password(username, password):
    user = db.session.scalar(sa.Select(User).where(User.username==username))
    if user and user.check_password(password):
        return user
    return None
    
@basic_auth.error_handler
def error_handler(status):
    return error_response(status)

@token_auth.verify_token
def verify_token(token):
    return User.check_token(token) if token else None

@token_auth.error_handler
def error_handler(status):
    return error_response(status)