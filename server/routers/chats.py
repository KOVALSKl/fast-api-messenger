from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from database import DataBaseConnector
from database.models import Chat, Message
from typing import List

router = APIRouter(
    prefix='/{user_login}/chats',
    tags=['chats'],
    responses={404: {"description": 'Not Found'}}
)

connection = DataBaseConnector()
database = connection.db


@router.get('/')
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


@router.get('/{chat_id}')
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


@router.post('/')
async def create_chat(user_login: str, members_logins: List[str], chat_name: str = ''):
    try:
        chat_members = list(set(filter(lambda member: member != user_login, members_logins)))

        for member in chat_members:
            user = root_collection_item_exist('users', member)
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


@router.post('/{chat_id}')
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