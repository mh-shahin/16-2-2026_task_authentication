from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings


pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)




def verify_password(plain_password: str, hash_password: str) -> bool:
    return pwd_context.verify(plain_password, hash_password)





def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)





def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


    

def create_reset_password_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_OTP_EXPIRE_MINUTES)
    to_encode = {'sub': email, 'exp': expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)





def verify_reset_password_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if email is None:
            return None
        return email
    except JWTError:
        return None