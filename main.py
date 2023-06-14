from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta

from database.models import User, Role
from database import DataBaseConnector

import bcrypt
import os
import jwt
import json

from dotenv import load_dotenv
load_dotenv()

HASH_KEY = os.environ.get('HASH_KEY').encode('utf-8')
JWT_KEY = os.environ.get('JWT_TOKEN_KEY')

app = FastAPI()
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


@app.get('/{user_login}')
async def get_user(user_login):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            return JSONResponse(content=user_doc.to_dict(), status_code=200)

        HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/posts')
async def get_user_posts(user_login):
    return {"user_login": user_login}


@app.get('/{user_login}/posts/{post_id}')
async def get_user_post(user_login, post_id):
    return {"user_login": user_login, 'post_id': post_id}


@app.get('/{user_login}/friends')
async def get_user_friends(user_login):
    return {"user_login": user_login}


@app.get('/{user_login}/friends/{friend_login}')
async def get_user_friend(user_login, friend_login):
    return {"user_login": user_login, 'friend_login': friend_login}


@app.post('/signup')
async def signup(user: User):
    try:
        doc_ref = database.collection('users').document(user.login)

        encoded_pass = user.password.encode('utf-8')
        hashed_pass = bcrypt.hashpw(encoded_pass, HASH_KEY)

        doc_ref.set({
            'login': user.login,
            'email': user.email,
            'password': hashed_pass,
            'role': Role.USER
        })

        # верификация email

        user_obj_dict = user.dict(include={'login': True, 'role': True})
        jwt_token = jwt.encode(payload=user_obj_dict, key=JWT_KEY)

        response = JSONResponse(content={'token': jwt_token}, status_code=200)
        response.set_cookie(key='token', value=jwt_token, expires=timedelta(hours=24))

        return response
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)


@app.post('/login')
async def login(user: User):
    try:
        doc_ref = database.collection('users').document(user.login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_document_dict = user_doc.to_dict()
            encoded_pass = user.password.encode('utf-8')
            hashed_pass = bcrypt.hashpw(encoded_pass, HASH_KEY)

            if bcrypt.checkpw(hashed_pass, user_document_dict['password']):
                return HTTPException(detail={'message': 'Wrong Password'}, status_code=403)
            
            user_obj_dict = user.dict(include={'login': True, 'role': True})
            jwt_token = jwt.encode(payload=user_obj_dict, key=JWT_KEY)

            response = JSONResponse(content={'token': jwt_token}, status_code=200)
            response.set_cookie(key='token', value=jwt_token, expires=timedelta(hours=24))

            return response
        else:
            return HTTPException(detail={'message': 'Wrong User Login'}, status_code=403)
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)