from datetime import date
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Task,Priority
from app.schemas import TaskIn
from app.security import current_user
from app.services.progress import complete_task,reopen_task
r=APIRouter(prefix='/tasks',tags=['tasks'])
@r.get('')
async def list_tasks(from_date:date|None=None,to_date:date|None=None,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    q=select(Task).where(Task.owner_id==u.id)
    if from_date:q=q.where(Task.task_date>=from_date)
    if to_date:q=q.where(Task.task_date<=to_date)
    return (await db.execute(q.order_by(Task.task_date,Task.created_at))).scalars().all()
@r.post('',status_code=201)
async def create(x:TaskIn,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    try:p=Priority(x.priority)
    except:raise HTTPException(422,'Priority must be Low, Medium, or High')
    t=Task(owner_id=u.id,title=x.title.strip(),category=x.category,priority=p,task_date=x.task_date); db.add(t); await db.commit(); await db.refresh(t); return t
@r.patch('/{task_id}/toggle')
async def toggle(task_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    t=await db.scalar(select(Task).where(Task.id==task_id,Task.owner_id==u.id).with_for_update())
    if not t:raise HTTPException(404,'Task not found')
    await (reopen_task(db,t) if t.completed else complete_task(db,t)); await db.commit(); await db.refresh(t); return t
@r.delete('/{task_id}',status_code=204)
async def delete(task_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    t=await db.scalar(select(Task).where(Task.id==task_id,Task.owner_id==u.id))
    if not t:raise HTTPException(404,'Task not found')
    if t.completed: await reopen_task(db,t)
    await db.delete(t); await db.commit()
