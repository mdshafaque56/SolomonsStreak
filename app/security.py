import hashlib, secrets, uuid
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import User
password_hasher=PasswordHash.recommended(); bearer=HTTPBearer(auto_error=False)
def hash_password(v): return password_hasher.hash(v)
def verify_password(v,h): return password_hasher.verify(v,h)
def access_token(user_id):
    now=datetime.now(timezone.utc); return jwt.encode({'sub':str(user_id),'type':'access','iat':now,'exp':now+timedelta(minutes=settings.access_token_minutes)},settings.secret_key,algorithm='HS256')
def new_refresh(): return secrets.token_urlsafe(48)
def token_hash(v): return hashlib.sha256(v.encode()).hexdigest()
def decode_access(v):
    try:
        p=jwt.decode(v,settings.secret_key,algorithms=['HS256']);
        if p.get('type')!='access': raise JWTError()
        return uuid.UUID(p['sub'])
    except Exception: raise HTTPException(401,'Invalid or expired access token',headers={'WWW-Authenticate':'Bearer'})
async def current_user(c:HTTPAuthorizationCredentials=Depends(bearer),db:AsyncSession=Depends(get_db)):
    if not c: raise HTTPException(401,'Authentication required')
    u=await db.get(User,decode_access(c.credentials))
    if not u or not u.is_active: raise HTTPException(401,'Inactive or missing user')
    return u
