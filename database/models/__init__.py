from pydantic import BaseModel, Field, SecretStr, EmailStr, PrivateAttr
from typing import Optional
from datetime import date
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
    created_at: date = date.today()

