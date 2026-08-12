from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import UserStats,FocusSession
from app.schemas import FocusIn
from app.security import current_user
from app.services.progress import ensure_stats
r=APIRouter(prefix='/progress',tags=['progress'])
@r.get('')
async def progress(u=Depends(current_user),db:AsyncSession=Depends(get_db)): return await db.get(UserStats,u.id)
@r.post('/focus',status_code=201)
async def focus(x:FocusIn,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    s=await ensure_stats(db,u.id); s.focus_minutes+=x.minutes; s.focus_sessions+=1; s.score+=x.minutes
    f=FocusSession(user_id=u.id,minutes=x.minutes); db.add(f); await db.commit(); return {'minutes':x.minutes,'score':s.score,'focus_minutes':s.focus_minutes,'focus_sessions':s.focus_sessions}
