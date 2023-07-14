from lib import verify_password, get_password_hash, \
    create_access_token, root_collection_item_exist
from database.models import User, BaseUserModel
from database import DataBaseConnector

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

from jose import JWTError, jwt
from config import Configuration

connection = DataBaseConnector()
firebase = connection.db

config = Configuration()
config.read()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_user(user_login: str):
    user_ref = root_collection_item_exist(firebase, 'users', user_login)
    if user_ref:
        user_dict = (user_ref.get()).to_dict()
        model = BaseUserModel(**user_dict)
        return model


def authenticate_user(user_login: str, password: str):
    user = get_user(user_login)
    if not user:
        return False
    if not verify_password(password, user.password.get_secret_value()):
        return False
    return user
