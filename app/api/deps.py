from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_auth import User
from app.core.security import decode_access_token
from app.models.auth import User
from app.database import supabase
from app.schemas.CommonResponse import ApiResponse
from app.database import get_db
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer()

def get_current_user(credentials : HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
            headers={'WWW-Authenticate': 'Bearer'}
            )
    
    email = payload.get('sub')
    role = payload.get('role')
    id = payload.get('user_id')
    
    if not email:
        raise HTTPException(status_code=401, detail='Token payload invalid')
    
    return{'email':email, 'role': role, 'id': id}







def require_admin(current_user: dict = Depends(get_current_user)):

    return current_user






def require_event_manager(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    
    return current_user






def require_user_or_manager(current_user: dict = Depends(get_current_user)):
    
    return current_user
    