from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

import lib
from database import DataBaseConnector
from database.models import Chat, Message, Notification, NotificationType, BaseUserModel, ChatMeta
from typing import List, Union

from lib import root_collection_item_exist, create_chat, \
    create_dialog, send_notification_to_chat_members, get_user_from_token
from config import Configuration
from jose import jwt

router = APIRouter(
    prefix='/chats',
    tags=['chats'],
    responses={404: {"description": 'Not Found'}}
)

connection = DataBaseConnector()
database = connection.db

config = Configuration()
config.read()

JWT_HASH_KEY = config['keys']['jwt']
CRYPT_ALGORITHM = config['crypt_settings']['algorithm']


@router.get('/')
async def get_all_user_chats(request: Request):
    """
        Получение всех чатов пользователя
        :param request: Объект запроса
        :return:
        """
    try:
        user = get_user_from_token(request)

        if not user:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = root_collection_item_exist(database, 'users', user.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        user_chats = []
        for chat in user_ref.collection('chats').stream():
            chat_model = chat.to_dict()
            user_chats.append(chat_model)
        return JSONResponse(content={'chats': user_chats}, status_code=200)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@router.get('/{chat_id}')
async def get_user_chat(request: Request, chat_id: str):
    """
    Получение конкретного чата/диалога пользователя по идентификатору чата
    :param request: Объект запроса
    :param chat_id: Идентификатор чата
    :return:
    """
    try:
        user = get_user_from_token(request)

        if not user:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        chat_ref = root_collection_item_exist(database, 'chats', chat_id)
        user_ref = root_collection_item_exist(database, 'users', user.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        if not chat_ref:
            return HTTPException(detail={'message': f"The chat {chat_id} doesn't exist"}, status_code=404)

        chat_dict = chat_ref.get().to_dict()
        chat_model = Chat(**chat_dict)

        if user.login not in chat_model.members:
            return HTTPException(detail={'message': f"The user {user.login} is not a chat member"},
                                 status_code=403)

        return JSONResponse(content=chat_dict, status_code=200)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@router.post('/')
async def create_chat(request: Request, members_login: List[str], chat_name: str = ''):
    """
    Создает чат/диалог
    :param request: Объект запроса
    :param members_login: Логины участников
    :param chat_name: Название чата (не диалога)
    :return:
    """

    try:
        creator = get_user_from_token(request)

        if not creator:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = root_collection_item_exist(database, 'users', creator.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        chat_members_login = list(set(filter(lambda member: member != creator.login, members_login)))

        for member in chat_members_login:
            member_ref = root_collection_item_exist(database, 'users', member)
            if not member_ref:
                return HTTPException(detail={'message': f"The user {member} doesn't exist"}, status_code=404)

        if len(chat_members_login) == 1:
            member_ref = root_collection_item_exist(database, 'users', members_login[0])
            chat = create_dialog(database, user_ref, member_ref)
        elif len(chat_members_login) > 1:
            chat_members_login.append(creator.login)
            chat = lib.create_chat(database, chat_members_login, chat_name)
        else:
            return HTTPException(detail={'message': f"Невозможно создать чат без участников"}, status_code=400)
        if not chat:
            return HTTPException(detail={'message': "Не удалось создать чат"}, status_code=500)

        response = JSONResponse(content=chat.dict(), status_code=200)
        return response
    except HTTPException as err:
        return err
    except Exception as err:
        return HTTPException(detail={'message': f"{err}"}, status_code=500)


@router.post('/{chat_id}')
async def send_message(request: Request, chat_id, message_content):
    """
    Отправляет сообщение в конкретный чат
    :param request: Объект запроса
    :param chat_id: Идентификатор чата
    :param message_content: Контент сообщения
    :return:
    """
    user = get_user_from_token(request)

    if not user:
        return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

    user_ref = root_collection_item_exist(database, 'users', user.login)
    chat_ref = root_collection_item_exist(database, 'chats', chat_id)

    if not user_ref:
        raise HTTPException(detail={'message': f"Пользователя {user.login} не существует"}, status_code=401)

    if not chat_ref:
        raise HTTPException(detail={'message': f"Чата {chat_id} не существует"}, status_code=400)

    chat_doc = chat_ref.get()
    chat_model = Chat(**chat_doc.to_dict())

    if user.login not in chat_model.members:
        return HTTPException(detail={'message': f"Нет доступа к чату"}, status_code=403)

    message = Message(
        creator_login=user.login,
        content=message_content
    )

    send_notification_to_chat_members(
        database,
        chat_model,
        user.login,
        Notification(
            type=NotificationType.MESSAGE,
            description=f'Пользователь {user.login} отправил сообщение',
            user=user.login,
            chat_id=chat_id
        )
    )

    update_time, message_ref = chat_ref.collection('messages').add(message.dict())

    return JSONResponse(content={'message': message_ref.id}, status_code=200)