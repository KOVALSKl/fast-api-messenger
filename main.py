from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import datetime

from database.models import User, Post, Subscription, Chat, Message, BaseUserModel
from typing import List, Union
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


def root_collection_item_exist(collection_name:str, item_id: str):
    item_ref = database.collection(collection_name).document(item_id)
    item_doc = item_ref.get()

    if item_doc.exists:
        return item_ref

    return None


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
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


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
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


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
        
        return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/followers')
async def get_user_followers(user_login):
    """
    Получение всех подписчиков пользователя
    :param user_login: Логин пользователя
    :return:
    """
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_obj = user_doc.to_dict()
            print(user_obj)
            user_followers = []
            for follower in doc_ref.collection('followers').stream():
                follower_obj = {'id': follower.id}
                follower_obj.update(follower.to_dict())
                user_followers.append(follower_obj)
            return JSONResponse(content={'followers': user_followers}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/following')
async def get_user_followers(user_login):
    """
    Получение всех подписок пользователя
    :param user_login: Логин пользователя
    :return:
    """
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_following = []
            for following in doc_ref.collection('following').stream():
                follower_obj = {'id': following.id}
                follower_obj.update(following.to_dict())
                user_following.append(follower_obj)
            return JSONResponse(content={'following': user_following}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/followers/{follower_login}')
async def get_user_friend(user_login, follower_login):
    return {"user_login": user_login, 'friend_login': follower_login}


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
    Отписывается на конкретного пользователя
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
                return HTTPException(detail={'message': f"The user {user_login} {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} {follower_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/chats')
async def get_all_user_chats(user_login):
    """
        Получение всех чатов пользователя
        :param user_login: Логин пользователя
        :return:
        """
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_chats = []
            for chat in doc_ref.collection('chats').stream():
                chat_obj = {'id': chat.id}
                chat_obj.update(chat.to_dict())
                user_chats.append(chat_obj)
            return JSONResponse(content={'chats': user_chats}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.get('/{user_login}/chats/{chat_id}')
async def get_user_chat(user_login, chat_id):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            chat_ref = database.collection('chats').document(chat_id)
            chat_doc = chat_ref.get()

            if chat_doc.exists:
                chat_member_ref = chat_ref.collection('members').document(user_login)
                chat_member_doc = chat_member_ref.get()

                if chat_member_doc.exists:
                    return JSONResponse(content=chat_doc.to_dict(), status_code=200)
                else:
                    return HTTPException(detail={'message': f"The user {user_login} is not a chat member"},
                                         status_code=400)
            else:
                return HTTPException(detail={'message': f"The chat {chat_id} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/{user_login}/chats')
async def create_chat(user_login: str, members_logins: List[str], chat_name: str = ''):
    try:
        chat_members = list(set(filter(lambda member: member != user_login, members_logins)))

        for member in chat_members:
            user = root_collection_item_exist('users',member)
            if not user:
                return HTTPException(detail={'message': f"The user {member} doesn't exist"}, status_code=400)

        if len(chat_members) == 1:
            user_ref = root_collection_item_exist('users', user_login)
            user_obj = user_ref.get()
            user_dict = user_obj.to_dict()

            friend_ref = root_collection_item_exist('users', chat_members[0])
            friend_obj = friend_ref.get()
            friend_dict = friend_obj.to_dict()

            if user_obj.exists and friend_obj.exists:
                user_chat_ref = user_ref.collection('chats').document(friend_dict['login'])
                user_chat_doc = user_chat_ref.get()

                friend_chat_ref = friend_ref.collection('chats').document(user_dict['login'])
                friend_chat_doc = friend_chat_ref.get()

                if user_chat_doc.exists and friend_chat_doc.exists:
                    pass
                else:
                    chat = Chat.parse_obj({
                        'members': members_logins,
                        'messages': []
                    })
                    update_time, chat_ref = database.collection('chats').add(chat.dict())
                    created_chat_obj = {'chat_id': chat_ref.id, 'created_at': chat.created_at}

                    user_chat_ref.set(created_chat_obj)
                    friend_chat_ref.set(created_chat_obj)

                    return JSONResponse(content={'message': f'chat id: {chat_ref.id}'}, status_code=200)
            else:
                return HTTPException(detail={'message': f"Bad request"}, status_code=400)

        elif len(members_logins) > 2:
            pass
        else:
            return HTTPException(detail={'message': f"A chat cannot consist of one participant"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/{user_login}/chats/{chat_id}')
async def send_message(user_login, chat_id, message_content):
    user = root_collection_item_exist('users', user_login)
    chat = root_collection_item_exist('chats', chat_id)

    if user:
        if chat:
            chat_doc = chat.get().to_dict()
            chat_obj = Chat.parse_obj(chat_doc)

            if user_login not in chat_obj.members:
                return HTTPException(detail={'message': f"You cannot send messages in this chat"}, status_code=400)

            message = Message.parse_obj({
                'creator_login': user_login,
                'content': message_content
            }).dict()

            update_time, message_ref = chat.collection('messages').add(message)

            return JSONResponse(content={'message': message_ref.id}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The chat doesn't exist"}, status_code=400)
    else:
        return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)

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