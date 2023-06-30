from pydantic import BaseModel, Field, SecretStr, EmailStr, PrivateAttr
from typing import Optional, Any, List, Union
import datetime
from enum import Enum, IntEnum


class Role(IntEnum, Enum):
    USER = 1,
    ADMIN = 2


class User(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    login: str
    email: Optional[EmailStr]
    password: SecretStr = Field(exclude=True)


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
    chat_name: Optional[str] = ''
    created_at: Optional[str] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    members: List[str]
    messages: List[Message]


class ChatMeta(BaseModel):
    chat_id: str
    created_at: str


class FollowsMeta(BaseModel):
    created_at: str


class BaseUserModel(User):
    chats: List[ChatMeta] = []
    followers: List[FollowsMeta] = []
    following: List[FollowsMeta] = []
    posts: List[Post] = []
    role: Role = Role.USER

    class Config:
        underscore_attrs_are_private = True
