from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import datetime

from database.models import User, Post, FriendRequest
from database import DataBaseConnector

import bcrypt
import os
import jwt

from dotenv import load_dotenv
load_dotenv()

HASH_KEY = os.environ.get('HASH_KEY').encode('utf-8')
JWT_KEY = os.environ.get('JWT_TOKEN_KEY')

app = FastAPI(
    title='Concat',
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


@app.get('/{user_login}')
async def get_user(user_login):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_obj = User.parse_obj(user_doc.to_dict())
            return JSONResponse(content={'user': user_obj.dict()}, status_code=200)

        HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/posts')
async def get_user_posts(user_login):

    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_posts = []
            for post in doc_ref.collection('posts').stream():
                post_obj = {'id': post.id}
                post_obj.update(post.to_dict())
                user_posts.append(post_obj)

            return JSONResponse(content={'posts': user_posts}, status_code=200)
        else:
            return HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/posts/{post_id}')
async def get_user_post(user_login, post_id):

    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            post_ref = doc_ref.collection('posts').document(post_id)
            post_doc = post_ref.get()

            if post_doc.exists:
                post_obj = post_doc.to_dict()
                return JSONResponse(content=post_obj, status_code=200)
            else:
                return HTTPException(detail={'message': "This post doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/{user_login}/posts/')
async def create_user_post(user_login, post: Post):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            post_obj_dict = post.dict()
            post_obj_dict.update({'created_at': post.created_at})
            post_ref = doc_ref.collection('posts').add(post_obj_dict)
            print(post_ref.id)
            return JSONResponse({'post': post_ref.id}, status_code=200)
        return HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/friends')
async def get_user_friends(user_login):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_friends = []
            for friend in doc_ref.collection('friends').stream():
                post_obj = {'id': friend.id}
                post_obj.update(friend.to_dict())
                user_friends.append(post_obj)

            return JSONResponse(content={'friends': user_friends}, status_code=200)
        else:
            return HTTPException(detail={'message': "This user doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/friends/{friend_login}')
async def get_user_friend(user_login, friend_login):
    return {"user_login": user_login, 'friend_login': friend_login}


@app.post('/{user_login}/friends/{friend_login}')
async def send_friend_request(user_login, friend_login, content):
    try:
        friend_ref = database.collection('users').document(friend_login)
        friend_doc = friend_ref.get()

        if friend_doc.exists:
            user_ref = database.collection('users').document(user_login)
            user_doc = user_ref.get()
            if user_doc.exists:

                received_friend_request = friend_ref.collection('friends_requests').document(user_login)
                received_friend_request_doc = received_friend_request.get()

                sent_friend_request = user_ref.collection('sent_requests').document(friend_login)
                sent_friend_request_doc = sent_friend_request.get()

                if sent_friend_request_doc.exists and received_friend_request_doc.exists:
                    pass
                else:
                    friend_request = FriendRequest.parse_obj({
                        'content': content
                    })

                    friend_request_dict = friend_request.dict()
                    friend_request_dict.update({'created_at': friend_request.created_at})

                    sent_friend_request.set(friend_request_dict)
                    received_friend_request.set(friend_request_dict)

                    return JSONResponse(content={'request': friend_request_dict}, status_code=200)
            else:
                return HTTPException(detail={'message': f"This user {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"This user {friend_login} doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.put('/{user_login}/friends/{friend_login}')
async def update_friend_request_status(user_login, friend_login):
    pass


@app.delete('/{user_login}/friends/{friend_login}')
async def delete_friend_request(user_login, friend_login):
    try:
        friend_ref = database.collection('users').document(friend_login)
        friend_doc = friend_ref.get()

        if friend_doc.exists:
            user_ref = database.collection('users').document(user_login)
            user_doc = user_ref.get()
            if user_doc.exists:

                received_friend_request = friend_ref.collection('friends_requests').document(user_login)
                received_friend_request_doc = received_friend_request.get()

                sent_friend_request = user_ref.collection('sent_requests').document(friend_login)
                sent_friend_request_doc = sent_friend_request.get()

                if sent_friend_request_doc.exists and received_friend_request_doc.exists:
                    sent_friend_request.delete()
                    received_friend_request.delete()
                    return JSONResponse(content={'message': 'Successfully deleted'}, status_code=200)
                else:
                    return HTTPException(detail={'message': "Request doesn't exists"}, status_code=400)
            else:
                return HTTPException(detail={'message': f"This user {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"This user {friend_login} doesn't exist"}, status_code=400)
    except:
        HTTPException(detail={'message': "Internal Error"}, status_code=500)

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
async def login(user: User):
    try:
        doc_ref = database.collection('users').document(user.login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_document_dict = user_doc.to_dict()
            encoded_pass = user.password.get_secret_value().encode('utf-8')
            hashed_pass = bcrypt.hashpw(encoded_pass, HASH_KEY)

            if bcrypt.checkpw(hashed_pass, user_document_dict['password']):
                return HTTPException(detail={'message': 'Wrong Password'}, status_code=403)
                
            user_obj = User.parse_obj(user_document_dict)
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