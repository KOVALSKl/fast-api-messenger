from fastapi import WebSocket, Request, WebSocketException
from fastapi.exceptions import HTTPException

from pydantic import BaseModel, EmailStr, PrivateAttr
from typing import Optional, Any, List, Union, Dict
import datetime
from enum import Enum, IntEnum

from lib import send_message
from database import DataBaseConnector

class Role(IntEnum, Enum):
    USER = 1,
    ADMIN = 2


class NotificationType(IntEnum, Enum):
    MESSAGE = 1,
    FOLLOWER = 2,
    POST = 3


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


class ChatResponse(Chat):
    messages: List[Message]


class FollowsMeta(BaseModel):
    created_at: str


class Notification(BaseModel):
    type: NotificationType
    description: str
    received_at: str = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    user: str
    chat_id: Optional[str]


class Endpoint:
    def __init__(self, method: RequestMethods, endpoint: str):
        self.method = method
        self.endpoint = endpoint


class WebSocketManager:

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(WebSocketManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.opened_connections: Dict[str, WebSocket] = []
        self.database = DataBaseConnector().db

    async def connect(self, user: BaseUserModel, websocket: WebSocket):
        await websocket.accept()
        self.opened_connections.update(
            {user.login: websocket}
        )

    def disconnect(self, user: BaseUserModel, websocket: WebSocket):
        try:
            del self.opened_connections[user.login]
        except KeyError:
            raise HTTPException(detail={'message': 'Соединения не существовало'})

    async def send_message_to_user(self, message: Message, user: BaseUserModel, chat_id: int):
        try:
            receiver = self.opened_connections[user.login]
            await receiver.send_json(message.dict())
            await send_message(self.database, user, chat_id, message)
        except KeyError:
            # проверить существование пользователя в бд
            # если он есть отправить ему сообщение и нотификейшон
            pass
        except WebSocketException:
            raise HTTPException(detail={'message': 'Проблема с соединением'})

    async def send_notification_to_all_users(self, notification: Notification):
        for connection in self.opened_connections.values():
            await connection.send_json(notification.dict())
