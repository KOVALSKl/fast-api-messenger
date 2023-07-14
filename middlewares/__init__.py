from fastapi import Request, HTTPException
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from jwt.exceptions import ExpiredSignatureError

from starlette import status
from starlette.responses import Response, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from database.models import Endpoint
from typing import List

import jwt
import os

load_dotenv()
JWT_KEY = os.environ.get('JWT_TOKEN_KEY')


class AuthorizationTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            if request.url.path not in ['/signup', '/login']:
                token = request.cookies["token"]

                payload = jwt.decode(
                    token,
                    JWT_KEY,
                    algorithms=['HS256']
                )
            response = await call_next(request)
            return response
        except (KeyError, ExpiredSignatureError):
            return RedirectResponse(
                '/login',
                status_code=status.HTTP_302_FOUND
            )


class AccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, available_endpoints: List[Endpoint]):
        super().__init__(app)
        self.available_endpoints = available_endpoints

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        try:
            token = request.cookies["token"]
            method = request.method
            request_endpoint = list(filter(lambda item: item != '', request.url.path.split('/')))

            payload = jwt.decode(
                token,
                JWT_KEY,
                algorithms=['HS256']
            )

            username = request_endpoint[0]
            for endpoint in self.available_endpoints:
                if username != payload['login']:
                    return HTTPException(detail={'Not authorized'}, status_code=403)

            response = await call_next(request)
            return response
        except (KeyError, ExpiredSignatureError):
            return RedirectResponse(
                '/login',
                status_code=status.HTTP_302_FOUND
            )




