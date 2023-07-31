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

        chat_ref = lib.root_collection_item_exist(database, 'chats', chat_id)
        user_ref = lib.root_collection_item_exist(database, 'users', user.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        if not chat_ref:
            return HTTPException(detail={'message': f"Чата {chat_id} не существует"}, status_code=404)

        chat_dict = chat_ref.get().to_dict()
        chat_model = Chat(**chat_dict)

        if user.login not in chat_model.members:
            return HTTPException(detail={'message': f"Пользователь {user.login} не является участником чата"},
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
        token_from_request = lib.get_token_from_request(request)
        creator = lib.get_user_from_token(token_from_request)

        if not creator:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        user_ref = lib.root_collection_item_exist(database, 'users', creator.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не существует"}, status_code=400)

        chat_members_login = list(set(filter(lambda member: member != creator.login, members_login)))

        for member in chat_members_login:
            member_ref = lib.root_collection_item_exist(database, 'users', member)
            if not member_ref:
                return HTTPException(detail={'message': f"Пользователь {member} не существует"}, status_code=404)

        if len(chat_members_login) == 1:
            member_ref = lib.root_collection_item_exist(database, 'users', members_login[0])
            chat = lib.create_dialog(database, user_ref, member_ref)
        elif len(chat_members_login) > 1:
            chat_members_login.append(creator.login)
            chat = lib.create_chat(database, chat_members_login, chat_name)
        else:
            return HTTPException(detail={'message': f"Невозможно создать чат без участников"}, status_code=400)
        if not chat:
            return HTTPException(detail={'message': "Не удалось создать чат"}, status_code=500)

        response = JSONResponse(content=chat.dict(), status_code=200)
        return response

        # здесь нужен редирект в созданный чат

    except HTTPException as err:
        return err
    except Exception as err:
        return HTTPException(detail={'message': f"{err}"}, status_code=500)


@router.websocket('/{chat_id}/ws/message')
async def message_websocket_communication(chat_id: str, websocket: WebSocket):
    try:
        chat_ref = lib.root_collection_item_exist(database, 'chats', chat_id)

        if not chat_ref:
            raise HTTPException(detail={'message': f"Чата {chat_id} не существует"}, status_code=404)

        chat_doc_obj = (chat_ref.get()).to_dict()
        chat_model = Chat(**chat_doc_obj)

        if not websocket:
            raise HTTPException(detail={'message': 'Не удалось установить соединение'}, status_code=400)

        await websocket_manager.connect(websocket)
        received_message_json = await websocket.receive_json()
        received_message_obj = ReceivedWebSocketMessage(**json.loads(received_message_json))

        user_model = lib.get_user_from_token(received_message_obj.auth_token)

        user_ref = lib.root_collection_item_exist(database, 'users', user_model.login)

        if not user_ref:
            return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

        if user_model not in chat_model.members:
            return HTTPException(detail={'message': f"Пользователь {user_model.login} не является участником чата"},
                                 status_code=403)

        for member in chat_model.members:
            if user_model.login == member:
                continue
            member_ref = lib.root_collection_item_exist(database, 'users', member)
            member_doc_obj = (member_ref.get()).to_dict()
            member_model = BaseUserModel(**member_doc_obj)

            member_connection = websocket_manager[member_model.login]
            if type(received_message_obj.message) == Message:
                await lib.send_websocket_message(chat_ref, received_message_obj.message, member_connection)

        websocket_message = WebSocketMessage(
            type=MessageType.MESSAGE,
            message=received_message_obj.message,
        )

        await websocket.send_json(websocket_message)

    except Exception as err:
        return HTTPException(detail={'message': f"{err}"}, status_code=500)