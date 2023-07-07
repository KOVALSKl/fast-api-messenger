from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from database import DataBaseConnector
from database.models import Notification, \
    MessageNotification, \
    FollowerNotification, \
    PostNotification

router = APIRouter(
    prefix='/{user_login}/notifications',
    tags=['notifications'],
    responses={404: {"description": 'Not found'}}
)

connection = DataBaseConnector()
database = connection.db

@router.get('/')
def all_notifications(user_login):
    pass
