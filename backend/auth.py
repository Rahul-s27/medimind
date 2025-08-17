import os
from fastapi import APIRouter, Body, HTTPException, Request
import jwt
from datetime import datetime, timedelta
from utils import verify_google_token

router = APIRouter()

@router.post('/verify')
async def verify_id_token(request: Request, id_token: str | None = Body(None, embed=True)):
    # Accept Google ID token from JSON body or Authorization: Bearer <id_token>
    token = id_token
    if not token:
        auth = request.headers.get('Authorization') or request.headers.get('authorization')
        if auth and auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail='Token missing: provide id_token in JSON body or Authorization header')

    user_info = verify_google_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail='Invalid Google ID token')
    # Issue JWT for your app
    jwt_secret = os.getenv('JWT_SECRET', 'dev-secret')
    payload = {
        'sub': user_info['sub'],
        'email': user_info.get('email'),
        'name': user_info.get('name'),
        'exp': datetime.utcnow() + timedelta(hours=12),
    }
    token_jwt = jwt.encode(payload, jwt_secret, algorithm='HS256')
    return {'token': token_jwt, 'user': user_info}
