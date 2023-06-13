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
    response = await call_next(request)
    token = response.headers["Authorization"].split()[1]

    try:
        payload = jwt.decode(
            token,
            key=JWT_KEY
        )

        jwt_token = jwt.encode(payload=payload, key=JWT_KEY)
        return JSONResponse(content={'token': jwt_token}, status_code=200)
    except ExpiredSignatureError as error:
        return HTTPException(detail={"message": "Invalid Authorization Token"}, status_code=401)
