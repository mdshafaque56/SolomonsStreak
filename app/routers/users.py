from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,or_,and_,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User,UserStats,Follow
from app.schemas import ProfileUpdate
from app.security import current_user
r=APIRouter(prefix='/users',tags=['users'])
def public(u,followed=False,follows_me=False): return {'id':u.id,'display_name':u.display_name,'avatar':u.avatar,'bio':u.bio,'presence':u.presence,'last_seen':u.last_seen,'followed':followed,'follows_me':follows_me,'mutual':followed and follows_me}
@r.get('/me')
async def me(u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    s=await db.get(UserStats,u.id); return {**public(u),'email':u.email,'phone':u.phone,'qualification':u.qualification,'address':u.address,'timezone':u.timezone,'stats':s}
@r.patch('/me')
async def update(x:ProfileUpdate,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    for k,v in x.model_dump(exclude_unset=True).items(): setattr(u,k,v)
    await db.commit(); return public(u)
@r.get('')
async def users(q:str='',limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    stmt=select(User).where(User.is_active==True,User.id!=u.id)
    if q: stmt=stmt.where(or_(User.display_name.ilike(f'%{q}%'),User.bio.ilike(f'%{q}%')))
    people=(await db.execute(stmt.order_by(User.presence,User.display_name).limit(limit).offset(offset))).scalars().all()
    outgoing=set((await db.execute(select(Follow.following_id).where(Follow.follower_id==u.id))).scalars())
    incoming=set((await db.execute(select(Follow.follower_id).where(Follow.following_id==u.id))).scalars())
    return [public(p,p.id in outgoing,p.id in incoming) for p in people]
@r.put('/{target_id}/follow',status_code=204)
async def follow(target_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if str(u.id)==target_id: raise HTTPException(400,'Cannot follow yourself')
    target=await db.get(User,target_id)
    if not target: raise HTTPException(404,'User not found')
    if not await db.scalar(select(Follow).where(Follow.follower_id==u.id,Follow.following_id==target.id)): db.add(Follow(follower_id=u.id,following_id=target.id)); await db.commit()
@r.delete('/{target_id}/follow',status_code=204)
async def unfollow(target_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    f=await db.scalar(select(Follow).where(Follow.follower_id==u.id,Follow.following_id==target_id))
    if f: await db.delete(f); await db.commit()
