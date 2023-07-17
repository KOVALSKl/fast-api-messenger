from fastapi.exceptions import HTTPException
from fastapi import Request
from passlib.context import CryptContext
from datetime import datetime, timedelta

from database.models import BaseUserModel, Chat, ChatMeta, Notification, NotificationType
from config import Configuration

from jose import JWTError, jwt, ExpiredSignatureError
from typing import Union
from uuid import uuid4

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


def create_access_token(user: BaseUserModel, expires_delta: timedelta = timedelta(days=1)):
    """
    Создание JWT токена для авторизации пользователя
    :param user: Пользователь
    :param expires_delta: Срок годности токена (по умолчанию 1 день)
    :return: Возвращает сформированный токен в виде строки
    """

    expires = datetime.utcnow() + expires_delta

    # если токен не будет установлен в кукисы, установим его сами
    # exp_str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    user_dict = user.dict()
    user_dict.update({'exp': expires})
    encoded_jwt = jwt.encode(user_dict, config['keys']['jwt'],
                             algorithm=config['crypt_settings']['algorithm'])

    return encoded_jwt


def create_dialog(database, creator_ref, member_ref) -> Union[ChatMeta, None]:
    creator_model = BaseUserModel(**creator_ref.get().to_dict())
    member_model = BaseUserModel(**member_ref.get().to_dict())

    creator_chat_ref = creator_ref.collection('chats').document(member_model.login)
    creator_chat_doc = creator_chat_ref.get()

    member_chat_ref = member_ref.collection('chats').document(creator_model.login)
    member_chat_doc = member_chat_ref.get()

    chat_meta = None

    if creator_chat_doc.exists and member_chat_doc.exists:
        raise HTTPException(detail={'message': 'Диалог существует'}, status_code=400)
    else:
        try:
            chat = Chat(
                members=[creator_model.login, member_model.login],
                messages=[],
            )

            update_time, chat_ref = database.collection('chats').add(chat.dict())
            chat_meta = ChatMeta(
                chat_id=chat_ref.id,
                created_at=update_time
            )

            creator_chat_ref.set(chat_meta.dict())
            member_chat_ref.set(chat_meta.dict())

        finally:
            return chat_meta


def create_chat(database, members, chat_name: str = uuid4()) -> Union[ChatMeta, None]:
    try:
        chat = Chat(
            members=members,
            chat_name=chat_name
        )
        chat_meta = None

        update_time, chat_ref = database.collection('chats').add(chat.dict())
        chat_meta = ChatMeta(
            chat_id=chat_ref.id,
            created_at=update_time
        )

        for member_login in members:
            member_ref = root_collection_item_exist(database, 'users', member_login)
            member_chat_ref = member_ref.collection('chats').document(chat_name)
            member_chat_ref.set(chat_meta.dict())
    finally:
        return chat_meta


def send_notification_to_chat_members(
        database,
        chat: Chat,
        sender_login,
        notification: Notification):
    for member in chat.members:
        if member != sender_login:
            member_ref = root_collection_item_exist(database, 'users', member)
            if member_ref:
                member_ref.collection('notifications').add(notification.dict())


def get_user_from_token(request: Request) -> Union[BaseUserModel, None]:
    try:
        user = None
        token = request.cookies.get('token')
        user = BaseUserModel.parse_obj(jwt.decode(token, JWT_HASH_KEY, algorithms=CRYPT_ALGORITHM))

    except (JWTError, ExpiredSignatureError, KeyError):
        raise HTTPException(detail={'message': 'Пользователь не авторизован'}, status_code=401)
    finally:
        return user