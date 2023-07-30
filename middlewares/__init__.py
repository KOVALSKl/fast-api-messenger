from fastapi import Request
from fastapi import status
from fastapi.exceptions import HTTPException

from starlette.responses import Response, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from database.models import Endpoint
from config import Configuration

from typing import List
from jose import jwt, ExpiredSignatureError, JWTError


config = Configuration()
config.read()

JWT_HASH_KEY = config['keys']['jwt']
HASH_ALGORITHM = config['crypt_settings']['algorithm']


class AuthTokenExist(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        try:
            endpoint = request.url.path
            print(endpoint)
            token = request.headers["Authorization"].split()[1]
            payload = jwt.decode(
                token,
                JWT_HASH_KEY,
                algorithms=HASH_ALGORITHM
            )
            response = await call_next(request)
            return response
        except (KeyError, ExpiredSignatureError, JWTError):
            return HTTPException(
                detail={'message': 'Пользователь не авторизован'},
                status_code=status.HTTP_401_UNAUTHORIZED
            )