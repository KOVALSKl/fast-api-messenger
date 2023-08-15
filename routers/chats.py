from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

import lib
import json
from database import DataBaseConnector
from database.models import *
from typing import List
from config import Configuration

router = APIRouter(
    prefix='/chats',
    tags=['chats'],
    responses={404: {"description": 'Not Found'}}
)

connection = DataBaseConnector()
database = connection.db

websocket_manager = WebSocketManager()

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
        token_from_request = lib.get_token_from_request(request)
        user = lib.get_user_from_token(token_from_request)

        if not user:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = lib.root_collection_item_exist(database, 'users', user.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        user_chats = []
        for chat in user_ref.collection('chats').stream():
            # подумай как изменить это
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
        token_from_request = lib.get_token_from_request(request)
        user = lib.get_user_from_token(token_from_request)

        if not user:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = lib.root_collection_item_exist(database, 'users', user.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        chat_ref = lib.root_collection_item_exist(database, 'chats', chat_id)

        if not chat_ref:
            return HTTPException(detail={'message': f"Чата {chat_id} не существует"}, status_code=404)

        chat_dict = chat_ref.get().to_dict()
        chat_model = Chat(**chat_dict)

        if user.login not in chat_model.members:
            return HTTPException(detail={'message': f"Пользователь {user.login} не является участником чата"},
                                 status_code=403)

        messages = []

        for message_doc in chat_ref.collection('messages').stream():
            message_obj = message_doc.to_dict()
            messages.append(message_obj)

        messages.sort(key=lambda message: message['created_at'])

        chat_dict.update({'messages': messages})

        return JSONResponse(content=chat_dict, status_code=200)
    except Exception as err:
        return HTTPException(500, f'error: {err}')


@router.post('/')
async def create_chat(request: Request, chat_request_model: ChatModelRequest):
    """
    Создает чат/диалог
    :param chat_request_model: Модель данных для создания чата
    :param request: Объект запроса
    :return:
    """

    try:
        token_from_request = lib.get_token_from_request(request)
        creator = lib.get_user_from_token(token_from_request)

        if not creator:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = lib.root_collection_item_exist(database, 'users', creator.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        chat_members_login = list(set(filter(lambda member: member != creator.login, chat_request_model.members_login)))

        for member in chat_members_login:
            member_ref = lib.root_collection_item_exist(database, 'users', member)
            if not member_ref:
                return HTTPException(detail={'message': f"Пользователь {member} не существует"}, status_code=404)

        if len(chat_members_login) == 1:
            member_ref = lib.root_collection_item_exist(database, 'users', chat_request_model.members_login[0])
            chat = lib.create_dialog(database, user_ref, member_ref)
        elif len(chat_members_login) > 1:
            chat_members_login.append(creator.login)
            chat = lib.create_chat(database, chat_members_login, chat_request_model.chat_name)
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