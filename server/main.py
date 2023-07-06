import json
from typing import Union

import starlette.requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jwt.exceptions import ExpiredSignatureError
import datetime

from database.models import User, Subscription, BaseUserModel
from database import DataBaseConnector

from routers import posts, followers, following, chats

import bcrypt
import os
import jwt
import starlette.status as status

from dotenv import load_dotenv
load_dotenv()

HASH_KEY = os.environ.get('HASH_KEY').encode('utf-8')
JWT_KEY = os.environ.get('JWT_TOKEN_KEY')

app = FastAPI(
    title='Touch',
    description="The description",
    version='062023.1'
)
allow_all = ['*']
app.add_middleware(
   CORSMiddleware,
   allow_origins=allow_all,
   allow_credentials=True,
   allow_methods=allow_all,
   allow_headers=allow_all
)

connection = DataBaseConnector()
database = connection.db

app.include_router(posts.router)
app.include_router(followers.router)
app.include_router(following.router)
app.include_router(chats.router)


@app.get('/{user_login}')
async def get_user(user_login):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_obj = User.parse_obj(user_doc.to_dict())
            return JSONResponse(content={'user': user_obj.dict()}, status_code=200)

        return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/{user_login}/follow')
async def follow(user_login, follower_login: str):
    """
    Подписывается на конкретного пользователя
    :param user_login: Логин пользователя на которого подписываются
    :param follower_login: Логин пользователя который подписывается
    :return:
    """
    try:
        following_user_ref = database.collection('users').document(user_login)
        following_user_doc = following_user_ref.get()

        if following_user_doc.exists:
            follower_user_ref = database.collection('users').document(follower_login)
            follower_user_doc = follower_user_ref.get()

            if follower_user_doc.exists:

                follower_ref = following_user_ref.collection('followers').document(follower_login)
                follower_doc = follower_ref.get()

                following_ref = follower_user_ref.collection('following').document(user_login)
                following_doc = following_ref.get()

                if follower_doc.exists or following_doc.exists:
                    return HTTPException(detail={'message': f"You're already subscribers"}, status_code=400)

                subscription = Subscription()
                subscription_dict = subscription.dict()

                follower_ref.set(subscription_dict)
                following_ref.set(subscription_dict)

                return JSONResponse(content=subscription_dict, status_code=200)

            else:
                return HTTPException(detail={'message': f"The user {user_login} {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} {follower_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.delete('/{user_login}/unfollow')
async def unfollow(user_login, follower_login: str):
    """
    Отписывается от конкретного пользователя
    :param user_login: Логин пользователя от которого отписываются
    :param follower_login: Логин пользователя который отписывается
    :return:
    """
    try:
        following_user_ref = database.collection('users').document(user_login)
        following_user_doc = following_user_ref.get()

        if following_user_doc.exists:
            follower_user_ref = database.collection('users').document(follower_login)
            follower_user_doc = follower_user_ref.get()

            if follower_user_doc.exists:

                follower_ref = following_user_ref.collection('followers').document(follower_login)
                follower_doc = follower_ref.get()

                following_ref = follower_user_ref.collection('following').document(user_login)
                following_doc = following_ref.get()

                if not (follower_doc.exists or following_doc.exists):
                    return HTTPException(detail={'message': f"You're not a subscribers"}, status_code=400)

                following_ref.delete()
                follower_ref.delete()

                return JSONResponse(content={'message': 'successfully unfollow'}, status_code=200)

            else:
                return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} {follower_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/signup')
async def signup(user: User):
    try:
        doc_ref = database.collection('users').document(user.login)

        encoded_pass = user.password.get_secret_value().encode('utf-8')
        hashed_pass = bcrypt.hashpw(encoded_pass, HASH_KEY)

        doc_ref.set({
            'login': user.login,
            'email': user.email,
            'password': hashed_pass,
            'role': user.role.value
        })

        # верификация email

        user_obj_dict = user.dict()
        user_obj_dict.update({'role': user.role.value})

        jwt_token = jwt.encode(payload=user_obj_dict, key=JWT_KEY)

        response = JSONResponse(content={'token': jwt_token}, status_code=200)

        expires = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        response.set_cookie(key='token', value=jwt_token, expires=expires)

        return response
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)


@app.post('/login')
async def login(request: Request):
    try:
        request_body = await request.body()
        request_body_dict = json.loads(request_body.decode('utf-8'))
        user = User.parse_obj(request_body_dict)

        doc_ref = database.collection('users').document(user.login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_document_dict = user_doc.to_dict()
            encoded_pass = user.password.get_secret_value().encode('utf-8')
            hashed_pass = bcrypt.hashpw(encoded_pass, HASH_KEY)

            if bcrypt.checkpw(hashed_pass, user_document_dict['password']):
                return HTTPException(detail={'message': 'Wrong Password'}, status_code=403)

            user_obj = BaseUserModel.parse_obj(user_document_dict)
            user_obj_dict = user_obj.dict()
            user_obj_dict.update({'role': user_obj.role})

            jwt_token = jwt.encode(payload=user_obj_dict, key=JWT_KEY)

            response = JSONResponse(content={'token': jwt_token}, status_code=200)

            expires = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

            response.set_cookie(key='token', value=jwt_token, expires=expires)
            return response
        else:
            return HTTPException(detail={'message': 'Wrong User Login'}, status_code=403)
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)


@app.middleware('http')
async def authorization_token_check(request: Request, call_next):
    try:
        if request.url.path not in ['/signup', '/login']:
            token = request.cookies["token"]

            payload = jwt.decode(
                token,
                JWT_KEY,
                algorithms=['HS256']
            )
        response = await call_next(request)
        return response
    except (KeyError, ExpiredSignatureError):
        return RedirectResponse(
            '/login',
            status_code=status.HTTP_302_FOUND
        )