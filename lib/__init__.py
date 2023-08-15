from fastapi.exceptions import HTTPException
from fastapi import Request, WebSocket, WebSocketException
from passlib.context import CryptContext
from datetime import datetime, timedelta

# from database.models import BaseUserModel, Chat, ChatMeta, \
#     Notification, Token, MessageType, Message, WebSocketManager, WebSocketMessage
from config import Configuration

from jose import JWTError, jwt, ExpiredSignatureError
from typing import Union, Optional
from uuid import uuid4

import database.models as models

websocket_manager = models.WebSocketManager()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
config = Configuration()
config.read()

JWT_HASH_KEY = config['keys']['jwt']
CRYPT_ALGORITHM = config['crypt_settings']['algorithm']


def root_collection_item_exist(database, collection_name: str, item_id: str):
    """
    Получение документа из главной коллекции в базе Firestore
    :param database: Объект базы Firestore
    :param collection_name: Имя рутовой коллекции
    :param item_id: Уникальный идентификатор документа
    :return: Ссылку на документ в случае его существования в базе, иначе - None
    """
    item_ref = database.collection(collection_name).document(item_id)
    item_doc = item_ref.get()

    if item_doc.exists:
        return item_ref

    return None


def verify_password(plain_password, hashed_password):
    """
    Проверка совпадения хэшей пароля
    :param plain_password: Пароль введенный пользователем
    :param hashed_password: Хэшированный пароль из базы
    :return: True если хэши паролей совпали, False - иначе
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    """
    Хэширует пароль по схеме bcrypt
    :param password: Исходный пароль
    :return: Захэшированный пароль
    """
    return pwd_context.hash(password)


def create_access_token(user: models.BaseUserModel, expires_delta: timedelta = timedelta(days=1)):
    """
    Создание JWT токена для авторизации пользователя
    :param user: Пользователь
    :param expires_delta: Срок годности токена (по умолчанию 1 день)
    :return: Возвращает сформированный токен в виде строки
    """

    user_dict = user.dict()
    expires = datetime.utcnow()
    expires = (expires + expires_delta).strftime("%a, %d %b %Y %H:%M:%S GMT")
    # expires = (datetime.utcnow() + expires_delta).strftime("%a, %d %b %Y %H:%M:%S GMT")
    user_dict.update({'expires': expires})
    encoded_jwt = jwt.encode(user_dict, config['keys']['jwt'],
                             algorithm=config['crypt_settings']['algorithm'])

    token = models.Token(access_token=encoded_jwt, token_type='Bearer', expires=expires)

    return token


def create_dialog(database, creator_ref, member_ref) -> Union[models.ChatMeta, None]:
    creator_model = models.BaseUserModel(**creator_ref.get().to_dict())
    member_model = models.BaseUserModel(**member_ref.get().to_dict())

    creator_chat_ref = creator_ref.collection('chats').document(member_model.login)
    creator_chat_doc = creator_chat_ref.get()

    member_chat_ref = member_ref.collection('chats').document(creator_model.login)
    member_chat_doc = member_chat_ref.get()

    creator_chat_meta = None

    try:
        if creator_chat_doc.exists and member_chat_doc.exists:
            raise HTTPException(detail={'message': 'Диалог существует'}, status_code=400)
        else:
            chat = models.Chat(
                members=[creator_model.login, member_model.login],
                messages=[],
            )

            update_time, chat_ref = database.collection('chats').add(chat.dict())

            creator_chat_meta = models.ChatMeta(
                chat_name=f'{member_model.name} {member_model.surname}',
                chat_id=chat_ref.id,
                created_at=chat.created_at,
            )

            member_chat_meta = models.ChatMeta(
                chat_name=f'{creator_model.name} {creator_model.surname}',
                chat_id=chat_ref.id,
                created_at=chat.created_at
            )
            creator_chat_ref.set(creator_chat_meta.dict())
            member_chat_ref.set(member_chat_meta.dict())
    finally:
        return creator_chat_meta


def create_chat(database, members, chat_name: str = uuid4()) -> Union[models.ChatMeta, None]:

    chat_meta = None
    try:
        chat = models.Chat(
            members=members,
            chat_name=chat_name
        )
        update_time, chat_ref = database.collection('chats').add(chat.dict())
        chat_meta = models.ChatMeta(
            chat_name=chat_name,
            chat_id=chat_ref.id,
            created_at=chat.created_at
        )
        for member_login in members:
            member_ref = root_collection_item_exist(database, 'users', member_login)
            member_chat_ref = member_ref.collection('chats').document(chat_name)
            member_chat_ref.set(chat_meta.dict())
    finally:
        return chat_meta


def get_token_from_request(request: Request) -> str:
    """
    Получение токена из заголовка Authorization в запросе
    :param request: Объект запроса
    :return: Возвращает строку токена
    """
    token = request.headers.get('Authorization').split()[1]
    return token


def get_user_from_token(token: str) -> Union[models.BaseUserModel, None]:
    """
    Получение пользователя из JWT токена
    :param token: JWT токен
    :return: Возвращает модель пользователя или None
    """
    user = None
    try:
        decoded_jwt = jwt.decode(token, JWT_HASH_KEY, algorithms=CRYPT_ALGORITHM)
        user = models.BaseUserModel.parse_obj(decoded_jwt)

    except (JWTError, ExpiredSignatureError):
        raise HTTPException(detail={'message': 'Пользователь не авторизован'}, status_code=401)
    finally:
        return user


async def send_websocket_message(chat_id: str, message: models.Message, websocket: Optional[WebSocket]):
    """
    Сохраняет сообщение в коллекции чата, а также, если передан объект websocket - отправляет
    созданное сообщение пользователю
    :param chat_id: Уникальный идентификатор чата
    :param message: Объект сообщения
    :param websocket: Объект соединения websocket с пользователем
    :return:
    """
    websocket_message = models.WebSocketMessage(
        type=models.MessageType.MESSAGE,
        content=message,
    )

    response_message = models.ResponseMessage(
        message=websocket_message,
        chat_id=chat_id
    )

    if websocket:
        await websocket.send_json(response_message.dict())
    return websocket_message


async def send_websocket_notification(user_ref, notification: models.Notification, websocket: Optional[WebSocket]):
    """
    Сохраняет уведомление в коллекции уведомлений пользователя, а также, если передан объект websocket - отправляет
    созданное уведомление пользователю
    :param user_ref: Ссылка на документ пользователя в базе данных
    :param notification: Объект уведомления
    :param websocket: Объект соединения websocket с пользователем
    :return:
    """
    sent_notification_info = user_ref.collection('notifications').add(notification.dict())

    websocket_message = models.WebSocketMessage(
        type=models.MessageType.NOTIFICATION,
        content=notification
    )

    if websocket:
        await websocket.send_json(websocket_message.dict())
    return sent_notification_info
