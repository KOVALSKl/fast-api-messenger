from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from database import DataBaseConnector

from lib import root_collection_item_exist

router = APIRouter(
    prefix='/{user_login}/notifications',
    tags=['notifications'],
    responses={404: {"description": 'Not found'}}
)

connection = DataBaseConnector()
database = connection.db

@router.get('/')
async def all_notifications(user_login):
    """
    Получение всех оповещений пользователя
    :param user_login: Логин пользователя
    :return:
    """
    try:
        user_ref = root_collection_item_exist(database, 'users', user_login)

        if user_ref:
            user_notifications = []
            for notification in user_ref.collection('notifications').stream():
                notification_obj = {'id': notification.id}
                notification_obj.update(notification.to_dict())
                user_notifications.append(notification_obj)
            return JSONResponse(content={'notifications': user_notifications}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)
