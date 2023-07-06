from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from database import DataBaseConnector
from database.models import Post

router = APIRouter(
    prefix='/{user_login}/posts',
    tags=['posts'],
    responses={404: {"description": 'Not Found'}}
)

connection = DataBaseConnector()
database = connection.db


@router.get('/')
async def get_user_posts(user_login):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            user_posts = []
            for post in doc_ref.collection('posts').stream():
                post_obj = {'id': post.id}
                post_obj.update(post.to_dict())
                user_posts.append(post_obj)

            return JSONResponse(content={'posts': user_posts}, status_code=200)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@router.get('/{post_id}')
async def get_user_post(user_login, post_id):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            post_ref = doc_ref.collection('posts').document(post_id)
            post_doc = post_ref.get()

            if post_doc.exists:
                post_obj = post_doc.to_dict()
                return JSONResponse(content=post_obj, status_code=200)
            else:
                return HTTPException(detail={'message': "This post doesn't exist"}, status_code=400)
        else:
            return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)


@router.post('/')
async def create_user_post(user_login, post: Post):
    try:
        doc_ref = database.collection('users').document(user_login)
        user_doc = doc_ref.get()

        if user_doc.exists:
            post_obj_dict = post.dict()
            post_obj_dict.update({'created_at': post.created_at})
            post_ref = doc_ref.collection('posts').add(post_obj_dict)
            return JSONResponse({'post': post_ref.id}, status_code=200)

        return HTTPException(detail={'message': f"The user {user_login} doesn't exist"}, status_code=400)
    except:
        return HTTPException(detail={'message': "Internal Error"}, status_code=500)