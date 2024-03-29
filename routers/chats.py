from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from google.cloud.firestore_v1 import FieldFilter

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

        messages_query = chat_ref.collection('messages').order_by('created_at')

        for message_doc in messages_query.stream():
            message_obj = message_doc.to_dict()
            messages.append(message_obj)

        if not chat_model.chat_name:
            user_ref_chats_meta_ref = user_ref.collection('chats')
            user_ref_chats_meta = (
                user_ref_chats_meta_ref
                .where(filter=FieldFilter(
                    'chat_id', '==', chat_id
                ))
                .stream()
            )

            chat_name = ''

            for chat_meta in user_ref_chats_meta:
                chat_meta_doc = chat_meta.to_dict()
                chat_name = chat_meta_doc['chat_name']

            chat_dict.update({'chat_name': chat_name})

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
            chat, member_chat_meta = lib.create_dialog(database, user_ref, member_ref)
            websocket_message = WebSocketMessage(
                type=MessageType.UPDATE_CHATS,
                content=member_chat_meta
            )
        elif len(chat_members_login) > 1:
            chat_members_login.append(creator.login)
            chat = lib.create_chat(database, chat_members_login, chat_request_model.name)
            websocket_message = WebSocketMessage(
                type=MessageType.UPDATE_CHATS,
                content=chat
            )
        else:
            return HTTPException(detail={'message': f"Невозможно создать чат без участников"}, status_code=400)
        if not chat:
            return HTTPException(detail={'message': "Не удалось создать чат"}, status_code=500)

        response_message = ResponseMessage(
            message=websocket_message,
            chat_id=chat.chat_id
        )

        for member in chat_members_login:
            if member == creator.login:
                continue

            active_member = websocket_manager[member]
            if active_member:
                await active_member.connection.send_json(response_message.dict())

        response = JSONResponse(content=chat.dict(), status_code=200)
        return response

    except HTTPException as err:
        return err
    except Exception as err:
        return HTTPException(detail={'message': f"{err}"}, status_code=500)