from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User,UserStats,RefreshToken
from app.schemas import Register,Login,TokenPair
from app.security import hash_password,verify_password,access_token,new_refresh,token_hash,current_user
from app.config import settings
r=APIRouter(prefix='/auth',tags=['auth'])
async def pair(db,u):
    raw=new_refresh(); db.add(RefreshToken(user_id=u.id,token_hash=token_hash(raw),expires_at=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_days))); await db.commit(); return TokenPair(access_token=access_token(u.id),refresh_token=raw)
@r.post('/register',response_model=TokenPair,status_code=201)
async def register(x:Register,db:AsyncSession=Depends(get_db)):
    email=x.email.lower().strip()
    if await db.scalar(select(User.id).where(User.email==email)): raise HTTPException(409,'Email already registered')
    u=User(email=email,password_hash=hash_password(x.password),display_name=x.display_name.strip(),timezone=x.timezone); db.add(u); await db.flush(); db.add(UserStats(user_id=u.id)); return await pair(db,u)
@r.post('/login',response_model=TokenPair)
async def login(x:Login,db:AsyncSession=Depends(get_db)):
    u=await db.scalar(select(User).where(User.email==x.email.lower().strip()))
    if not u or not verify_password(x.password,u.password_hash): raise HTTPException(401,'Invalid email or password')
    return await pair(db,u)
@r.post('/refresh',response_model=TokenPair)
async def refresh(refresh_token:str,db:AsyncSession=Depends(get_db)):
    t=await db.scalar(select(RefreshToken).where(RefreshToken.token_hash==token_hash(refresh_token),RefreshToken.revoked==False).with_for_update())
    if not t or t.expires_at<datetime.now(timezone.utc): raise HTTPException(401,'Invalid refresh token')
    t.revoked=True; u=await db.get(User,t.user_id); return await pair(db,u)
@r.post('/logout',status_code=204)
async def logout(refresh_token:str,db:AsyncSession=Depends(get_db)):
    t=await db.scalar(select(RefreshToken).where(RefreshToken.token_hash==token_hash(refresh_token))); 
    if t: t.revoked=True; await db.commit()
