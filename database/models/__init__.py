from pydantic import BaseModel, Field, SecretStr, EmailStr, PrivateAttr
from typing import Optional, Any
import datetime
from enum import Enum, IntEnum


class Role(IntEnum, Enum):
    USER = 1,
    ADMIN = 2


class User(BaseModel):
    login: str
    email: Optional[EmailStr]
    _role: Role = PrivateAttr(default=Role.USER)
    password: SecretStr = Field(exclude=True)

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, value: Role):
        self._role = value

    class Config:
        underscore_attrs_are_private = True


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


class FriendRequest(BaseModel):
    _created_at: str = PrivateAttr()
    content: str

    def __init__(self, **data: Any):
        super().__init__(**data)

        self._created_at = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

    @property
    def created_at(self):
        return self._created_at

