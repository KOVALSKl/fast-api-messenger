from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from database import DataBaseConnector

router = APIRouter(
    prefix='/{user_login}/followers',
    tags=['followers'],
    responses={404: {"description": 'Not Found'}}
)

connection = DataBaseConnector()
database = connection.db


@router.get('/')
async def get_user_followers(user_login):
    """
    Получение всех подписчиков пользователя
    :param user_login: Логин пользователя
    :return:
    """
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_obj = user_doc.to_dict()
            print(user_obj)
            user_followers = []
            for follower in doc_ref.collection('followers').stream():
                follower_obj = {'id': follower.id}
                follower_obj.update(follower.to_dict())
                user_followers.append(follower_obj)
            return JSONResponse(content={'followers': user_followers}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)