from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

from database.models import BaseUserModel
from config import Configuration


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
config = Configuration()
config.read()


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

