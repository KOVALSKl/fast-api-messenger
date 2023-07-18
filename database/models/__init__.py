from pydantic import BaseModel, Field, SecretStr, EmailStr, PrivateAttr
from typing import Optional, Any, List, Union
import datetime
from enum import Enum, IntEnum


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


class ChatResponse(Chat):
    messages: List[Message]


class FollowsMeta(BaseModel):
    created_at: str


class ChatMeta(BaseModel):
    chat_id: str
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
