from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from jwt.exceptions import ExpiredSignatureError

import jwt
import os

load_dotenv()
JWT_KEY = os.environ.get('JWT_TOKEN_KEY')

app = FastAPI()


@app.middleware("http")
async def authorization_token_check(request: Request, call_next):
    token = request.headers["Authorization"].split()[1]

    try:
        payload = jwt.decode(
            token,
            key=JWT_KEY
        )

        response = await call_next(request)
        return response
    except ExpiredSignatureError as error:
        return HTTPException(detail={"message": "Invalid Authorization Token"}, status_code=401)
