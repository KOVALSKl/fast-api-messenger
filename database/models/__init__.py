from fastapi import WebSocket
from fastapi.exceptions import HTTPException

from pydantic import BaseModel, EmailStr, PrivateAttr
from typing import Optional, Any, List, Union, Dict
import datetime
from enum import Enum, IntEnum
from database import DataBaseConnector


class MessageType(IntEnum, Enum):
    MESSAGE = 0,
    UPDATEUSERSTATUS = 1,


class Role(IntEnum, Enum):
    USER = 1,
    ADMIN = 2


class RequestMethods(Enum):
    GET = 'GET',
    POST = 'POST',
    PUT = 'PUT',
    DELETE = 'DELETE'


class Token(BaseModel):
    access_token: str
    token_type: str
    expires: str


class User(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    login: str
    email: Optional[EmailStr]


class BaseUserModel(User):
    role: Role = Role.USER
    password: str


class UserStatus(BaseModel):
    chat_id: Union[str, None] = None
    auth_token: str


class Post(BaseModel):
    title: str
    content: str
    _created_at: str = PrivateAttr()

    def __init__(self, **data: Any):
        super().__init__(**data)

        self._created_at = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

    @property
    def created_at(self):
        return self._created_at


class Subscription(BaseModel):
    created_at: Optional[str] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')


class Message(BaseModel):
    created_at: Optional[str] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    creator_login: str
    content: str


class Chat(BaseModel):
    chat_name: Optional[str] = None
    created_at: Optional[str] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    members: List[str]


class ChatMeta(BaseModel):
    chat_name: str
    chat_id: str
    created_at: str


class ChatModelRequest(BaseModel):
    members_login: List[str]
    name: Union[str, None]


class ChatModelResponse(Chat):
    messages: List[Message]


class Notification(BaseModel):
    description: str
    received_at: str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    user: str
    chat_id: Optional[str]


class Endpoint:
    def __init__(self, method: RequestMethods, endpoint: str):
        self.method = method
        self.endpoint = endpoint


class WebSocketMessage(BaseModel):
    type: MessageType
    content: Union[Message, UserStatus]


class ResponseMessage(BaseModel):
    message: WebSocketMessage
    chat_id: str


class OpenedConnection:
    def __init__(self, connection: WebSocket, user_status: Union[UserStatus, None] = None):
        self.connection = connection
        self.user_status = user_status


class WebSocketManager:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(WebSocketManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.opened_connections: Dict[str, OpenedConnection] = {}
        self.database = DataBaseConnector().db

    def __getitem__(self, item: str):
        """
        Возвращает пользователя из списка активных подключений
        :param item: Логин пользователя по которому берем соединение
        :return:
        """
        if item in self.opened_connections:
            return self.opened_connections[item]
        else:
            return None

    def update_user_status(self, user: BaseUserModel, status: UserStatus):
        try:
            self.opened_connections[user.login].user_status = status
        except KeyError:
            raise HTTPException(400, 'Пользователь не активен')

    async def connect(self, user: BaseUserModel, websocket: WebSocket):
        await websocket.accept()
        self.opened_connections.update(
            {user.login: OpenedConnection(
                connection=websocket,
                user_status=None
            )}
        )

    def disconnect(self, user: BaseUserModel):
        try:
            del self.opened_connections[user.login]
            # в базу сохранять последнее время активности
        except KeyError:
            raise HTTPException(400, 'Соединения не существовало')
