from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from database.models import User, Subscription, BaseUserModel, Token, WebSocketManager
from middlewares import AuthTokenExist
from database import DataBaseConnector
from config import Configuration

from routers import posts, followers, following, chats
from dependencies import authenticate_user, create_access_token, get_password_hash

from lib import root_collection_item_exist

config = Configuration()
config.read()

HASH_KEY = config['keys']['hash']
JWT_KEY = config['keys']['jwt']
CRYPT_ALGORITHM = config['crypt_settings']['algorithm']

app = FastAPI(
    title='Touch',
    description="The description",
    version='062023.1'
)
allow_all = ['*']
app.add_middleware(
   CORSMiddleware,
   allow_origins=allow_all,
   allow_credentials=True,
   allow_methods=allow_all,
   allow_headers=allow_all
)
#app.add_middleware(AuthTokenExist)

connection = DataBaseConnector()
database = connection.db

websocket_manager = WebSocketManager()

app.include_router(posts.router)
app.include_router(followers.router)
app.include_router(following.router)
app.include_router(chats.router)


@app.get('/{user_login}',
         response_model=User,
         summary='Получение основной информации о пользователе'
         )
async def get_user(user_login):
    """
    Возвращает информацию о пользователе
    :param user_login: Логин пользователя
    :return:
    """
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_obj = User.parse_obj(user_doc.to_dict())
            return JSONResponse(content={'user': user_obj.dict()}, status_code=200)

        return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/{user_login}/follow',
          response_model=Subscription,
          summary='Подписывается на конкретного пользователя'
          )
async def follow(user_login, follower_login: str):
    """
    Подписывается на конкретного пользователя
    :param user_login: Логин пользователя на которого подписываются
    :param follower_login: Логин пользователя который подписывается
    :return:
    """
    try:
        following_user_ref = database.collection('users').document(user_login)
        following_user_doc = following_user_ref.get()

        if following_user_doc.exists:
            follower_user_ref = database.collection('users').document(follower_login)
            follower_user_doc = follower_user_ref.get()

            if follower_user_doc.exists:

                follower_ref = following_user_ref.collection('followers').document(follower_login)
                follower_doc = follower_ref.get()

                following_ref = follower_user_ref.collection('following').document(user_login)
                following_doc = following_ref.get()

                if follower_doc.exists or following_doc.exists:
                    return HTTPException(detail={'message': f"You're already subscribers"}, status_code=400)

                subscription = Subscription()
                subscription_dict = subscription.dict()

                follower_ref.set(subscription_dict)
                following_ref.set(subscription_dict)

                return JSONResponse(content=subscription_dict, status_code=200)

            else:
                return HTTPException(detail={'message': f"The user {user_login} {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} {follower_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.delete('/{user_login}/unfollow', summary="Отписывается от конкретного пользователя",)
async def unfollow(user_login, follower_login: str):
    """
    Отписывается от конкретного пользователя
    :param user_login: Логин пользователя от которого отписываются
    :param follower_login: Логин пользователя который отписывается
    :return:
    """
    try:
        following_user_ref = database.collection('users').document(user_login)
        following_user_doc = following_user_ref.get()

        if following_user_doc.exists:
            follower_user_ref = database.collection('users').document(follower_login)
            follower_user_doc = follower_user_ref.get()

            if follower_user_doc.exists:

                follower_ref = following_user_ref.collection('followers').document(follower_login)
                follower_doc = follower_ref.get()

                following_ref = follower_user_ref.collection('following').document(user_login)
                following_doc = following_ref.get()

                if not (follower_doc.exists or following_doc.exists):
                    return HTTPException(detail={'message': f"You're not a subscribers"}, status_code=400)

                following_ref.delete()
                follower_ref.delete()

                return JSONResponse(content={'message': 'successfully unfollow'}, status_code=200)

            else:
                return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} {follower_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@app.post('/signup', summary="Регистрация пользователя")
async def signup(user: BaseUserModel):
    """
    Производит регистрацию пользователя
    :param user: Объект пользователя
    :return:
    """
    try:
        if root_collection_item_exist(database, 'users', user.login):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {user.login} already exist"
            )
        doc_ref = database.collection('users').document(user.login)

        user.password = get_password_hash(user.password)
        user_db_model: BaseUserModel = BaseUserModel(**user.dict())
        user_db_model_dict = user_db_model.dict()

        doc_ref.set(user_db_model_dict)

        token_model = create_access_token(user_db_model)
        response = JSONResponse(content=token_model.dict(), status_code=200)

        return response
    except:
        return HTTPException(detail={'message': 'Error Creating User'}, status_code=400)


@app.post('/login',
          response_model=Token,
          summary='Аутентификация пользователя'
          )
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token_model = create_access_token(user)
    response = JSONResponse(content=token_model.dict(), status_code=200)

    return response