from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserStats, Task, Priority
POINTS={Priority.low:10,Priority.medium:15,Priority.high:20}
async def ensure_stats(db,user_id):
    s=await db.get(UserStats,user_id,with_for_update=True)
    if not s: s=UserStats(user_id=user_id); db.add(s); await db.flush()
    return s
async def complete_task(db,task):
    s=await ensure_stats(db,task.owner_id); today=date.today()
    task.completed=True; task.completed_at=func.now(); s.completed_tasks+=1; s.score+=POINTS[task.priority]
    if s.last_active_date is None: s.current_streak=1
    elif s.last_active_date==today: pass
    elif s.last_active_date==today-timedelta(days=1): s.current_streak+=1
    else: s.current_streak=1
    s.last_active_date=today; s.longest_streak=max(s.longest_streak,s.current_streak)
    if s.current_streak in (7,30,100): s.score += {7:100,30:500,100:2000}[s.current_streak]
async def reopen_task(db,task):
    s=await ensure_stats(db,task.owner_id); task.completed=False; task.completed_at=None
    s.completed_tasks=max(0,s.completed_tasks-1); s.score=max(0,s.score-POINTS[task.priority])
    # Exact streak is rebuilt from distinct completion dates to make reopen idempotent.
    dates=(await db.execute(select(func.date(Task.completed_at)).where(Task.owner_id==task.owner_id,Task.completed==True).distinct().order_by(func.date(Task.completed_at).desc()))).scalars().all()
    today=date.today(); streak=0; cursor=today
    for d in dates:
        if d==cursor: streak+=1; cursor-=timedelta(days=1)
        elif d<cursor: break
    s.current_streak=streak; s.last_active_date=dates[0] if dates else None
