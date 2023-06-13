from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database.models import User
from database import DataBaseConnector

import bcrypt
import os
import jwt

from dotenv import load_dotenv
load_dotenv()

# HASH_KEY = os.environ.get('HASH_KEY').encode('utf-8')
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


@app.post('/signup')
async def signup(user: User):
    doc_ref = database.collection('users').document(user.login)
    # hashing password
    encoded_pass = user.password.encode('utf-8')
    hashed_pass = bcrypt.hashpw(encoded_pass, bcrypt.gensalt())

    try:
        await doc_ref.set({
            'login': user.login,
            'email': user.email,
            'password': hashed_pass
        })

        return JSONResponse(content={'message': f'Successfully created user {user.login}'}, status_code=200)
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)


@app.post('/login')
async def login(user: User):
    try:
        doc_ref = database.collection('users').document(user.login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_dict = user_doc.to_dict()

            if bcrypt.checkpw(user.password, user_dict['password']):
                return HTTPException(detail={'message': 'Wrong Password'}, status_code=403)

            jwt_token = jwt.encode(payload=user, key=JWT_KEY)
            return JSONResponse(content={'token': jwt_token}, status_code=200)
        else:
            return HTTPException(detail={'message': 'Wrong User Login'}, status_code=403)
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)