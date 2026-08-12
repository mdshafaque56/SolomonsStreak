import uuid
from fastapi import APIRouter,Depends,HTTPException,WebSocket,WebSocketDisconnect,Query
from sqlalchemy import select,or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db,SessionLocal
from app.models import User,Conversation,ConversationMember,Message
from app.schemas import TextIn
from app.security import current_user,decode_access
r=APIRouter(prefix='/chat',tags=['chat'])
class Hub:
    def __init__(self): self.rooms={}
    async def join(self,room,ws): await ws.accept(); self.rooms.setdefault(room,set()).add(ws)
    def leave(self,room,ws): self.rooms.get(room,set()).discard(ws)
    async def emit(self,room,data):
        dead=[]
        for ws in self.rooms.get(room,set()):
            try: await ws.send_json(data)
            except: dead.append(ws)
        for ws in dead:self.leave(room,ws)
hub=Hub()
async def get_direct(db,a,b):
    key=':'.join(sorted([str(a),str(b)])); c=await db.scalar(select(Conversation).where(Conversation.direct_key==key))
    if not c:
        c=Conversation(direct_key=key); db.add(c); await db.flush(); db.add_all([ConversationMember(conversation_id=c.id,user_id=a),ConversationMember(conversation_id=c.id,user_id=b)]); await db.commit(); await db.refresh(c)
    return c
@r.post('/direct/{target_id}')
async def direct(target_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if str(u.id)==target_id:raise HTTPException(400,'Cannot chat with yourself')
    if not await db.get(User,target_id):raise HTTPException(404,'User not found')
    return await get_direct(db,u.id,target_id)
@r.get('/{conversation_id}/messages')
async def history(conversation_id:str,limit:int=Query(50,le=100),before:uuid.UUID|None=None,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if not await db.scalar(select(ConversationMember).where(ConversationMember.conversation_id==conversation_id,ConversationMember.user_id==u.id)):raise HTTPException(403,'Not a member')
    q=select(Message).where(Message.conversation_id==conversation_id).order_by(Message.created_at.desc()).limit(limit)
    return list(reversed((await db.execute(q)).scalars().all()))
@r.websocket('/ws/{conversation_id}')
async def ws_chat(ws:WebSocket,conversation_id:str,token:str):
    try:user_id=decode_access(token)
    except: await ws.close(code=4401); return
    async with SessionLocal() as db:
        member=await db.scalar(select(ConversationMember).where(ConversationMember.conversation_id==conversation_id,ConversationMember.user_id==user_id))
        if not member:await ws.close(code=4403);return
    await hub.join(conversation_id,ws)
    try:
        while True:
            payload=await ws.receive_json(); content=str(payload.get('content','')).strip()
            if not content or len(content)>1000:continue
            async with SessionLocal() as db:
                m=Message(conversation_id=uuid.UUID(conversation_id),sender_id=user_id,content=content);db.add(m);await db.commit();await db.refresh(m)
            await hub.emit(conversation_id,{'id':str(m.id),'sender_id':str(user_id),'content':content,'created_at':m.created_at.isoformat()})
    except WebSocketDisconnect:hub.leave(conversation_id,ws)
