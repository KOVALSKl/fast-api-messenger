from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException

from database.models import DataBaseConnector, WebSocketManager, \
    WebSocketMessage, MessageType, Message, UserStatus, Chat, BaseUserModel, ResponseMessage
from config import Configuration

import lib

router = APIRouter(
    prefix='/communication',
    tags=['communication'],
)

connection = DataBaseConnector()
database = connection.db

websocket_manager = WebSocketManager()

config = Configuration()
config.read()

JWT_HASH_KEY = config['keys']['jwt']
CRYPT_ALGORITHM = config['crypt_settings']['algorithm']


@router.websocket('/ws')
async def communication(websocket: WebSocket, auth_token):
    user_model = lib.get_user_from_token(auth_token)
    user_ref = lib.root_collection_item_exist(database, 'users', user_model.login)

    if not user_ref:
        return HTTPException(detail={'message': f"Пользователь не авторизован"}, status_code=401)

    if not websocket:
        raise HTTPException(detail={'message': 'Не удалось установить соединение'}, status_code=400)

    chat_ref = None
    chat_model = None
    chat_id = None

    await websocket_manager.connect(user_model, websocket)

    try:
        while True:
            message_obj = WebSocketMessage(**(await websocket.receive_json()))
            if message_obj.type == MessageType.UPDATE_USER_STATUS:
                if type(message_obj.content) == UserStatus:
                    chat_ref = lib.root_collection_item_exist(database, 'chats', message_obj.content.chat_id)

                    if not chat_ref:
                        raise HTTPException(detail={'message': f"Чата {message_obj.content.chat_id} не существует"},
                                            status_code=404)

                    chat_doc_obj = (chat_ref.get()).to_dict()
                    chat_model = Chat(**chat_doc_obj)
                    chat_id = message_obj.content.chat_id

                    websocket_manager.update_user_status(user_model, message_obj.content)
            elif message_obj.type == MessageType.MESSAGE and chat_ref and chat_model:
                if type(message_obj.content) == Message:
                    message = message_obj.content
                    for member in chat_model.members:
                        if user_model.login == member:
                            continue
                        member_ref = lib.root_collection_item_exist(database, 'users', member)
                        member_doc_obj = (member_ref.get()).to_dict()
                        member_model = BaseUserModel(**member_doc_obj)

                        member_connection = websocket_manager[member_model.login]

                        if member_connection:
                            member_connection = member_connection.connection

                        websocket_message = await lib.send_websocket_message(chat_id, message, member_connection)

                    sent_message_info = chat_ref.collection('messages').add(message.dict())

                    response_message = ResponseMessage(
                        message=websocket_message,
                        chat_id=chat_id
                    )

                    await websocket.send_json(response_message.dict())
            else:
                raise HTTPException(400, 'Невозможно обработать запрос')

    except WebSocketDisconnect:
        websocket_manager.disconnect(user_model)
