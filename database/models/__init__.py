from pydantic import BaseModel, Field, SecretStr
from enum import Enum


class Role(Enum):
    USER = 1,
    ADMIN = 2


class User(BaseModel):
    login: str
    email: str
    password: SecretStr = Field(exclude=True)
    role: Role = Role.USER


