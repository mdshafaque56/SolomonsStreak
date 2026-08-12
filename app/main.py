from __future__ import annotations
import hashlib, hmac, json, os, secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Boolean, DateTime, ForeignKey, Text, Integer, UniqueConstraint, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./solomons.db').replace('postgres://','postgresql+psycopg://',1)
if DATABASE_URL.startswith('postgresql://'): DATABASE_URL=DATABASE_URL.replace('postgresql://','postgresql+psycopg://',1)
SECRET_KEY=os.getenv('SECRET_KEY','dev-only-change-this-key')
OWNER_EMAIL=os.getenv('OWNER_EMAIL','mdshafaque56@gmail.com').lower()
OWNER_PASSWORD=os.getenv('OWNER_PASSWORD','Rafna123@')
TOKEN_HOURS=int(os.getenv('ACCESS_TOKEN_HOURS','168'))
connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {}
engine=create_engine(DATABASE_URL,pool_pre_ping=True,connect_args=connect_args)
SessionLocal=sessionmaker(engine,expire_on_commit=False)
serializer=URLSafeTimedSerializer(SECRET_KEY,salt='solomons-auth')

def now(): return datetime.now(timezone.utc)
def hash_password(p:str,salt:str|None=None)->str:
    salt=salt or secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),260000)
    return f'{salt}${digest.hex()}'
def verify_password(p:str,stored:str)->bool:
    try: salt,digest=stored.split('$',1); return hmac.compare_digest(hash_password(p,salt),stored)
    except Exception: return False

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); email:Mapped[str]=mapped_column(String(320),unique=True,index=True); password_hash:Mapped[str]; display_name:Mapped[str]=mapped_column(String(80)); phone:Mapped[str|None]; qualification:Mapped[str|None]; address:Mapped[str|None]=mapped_column(Text); bio:Mapped[str|None]=mapped_column(String(200)); avatar:Mapped[str]=mapped_column(String(16),default='S'); role:Mapped[str]=mapped_column(String(20),default='user'); presence:Mapped[str]=mapped_column(String(20),default='online'); last_seen:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); state:Mapped['UserState']=relationship(back_populates='user',uselist=False,cascade='all,delete-orphan')
class UserState(Base):
    __tablename__='user_states'; user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True); payload:Mapped[str]=mapped_column(Text,default='{}'); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now); user:Mapped[User]=relationship(back_populates='state')
class Task(Base):
    __tablename__='tasks'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); title:Mapped[str]=mapped_column(String(160)); category:Mapped[str]=mapped_column(String(50),default='Work'); priority:Mapped[str]=mapped_column(String(20),default='Medium'); due_date:Mapped[str|None]=mapped_column(String(10)); due_time:Mapped[str|None]=mapped_column(String(5)); duration:Mapped[int]=mapped_column(Integer,default=30); notes:Mapped[str|None]=mapped_column(Text); completed:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class FocusSession(Base):
    __tablename__='focus_sessions'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True); kind:Mapped[str]=mapped_column(String(30),default='focus'); minutes:Mapped[int]; completed:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Post(Base):
    __tablename__='posts'; id:Mapped[int]=mapped_column(primary_key=True); author_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); text:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); edited_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); author:Mapped[User]=relationship(); comments:Mapped[list['Comment']]=relationship(cascade='all,delete-orphan'); likes:Mapped[list['PostLike']]=relationship(cascade='all,delete-orphan')
class PostLike(Base):
    __tablename__='post_likes'; __table_args__=(UniqueConstraint('post_id','user_id'),); id:Mapped[int]=mapped_column(primary_key=True); post_id:Mapped[int]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE')); user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'))
class Comment(Base):
    __tablename__='comments'; id:Mapped[int]=mapped_column(primary_key=True); post_id:Mapped[int]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE')); author_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); parent_id:Mapped[int|None]=mapped_column(ForeignKey('comments.id',ondelete='CASCADE')); text:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); edited_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); author:Mapped[User]=relationship(foreign_keys=[author_id])
class Follow(Base):
    __tablename__='follows'; __table_args__=(UniqueConstraint('follower_id','following_id'),); id:Mapped[int]=mapped_column(primary_key=True); follower_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); following_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Message(Base):
    __tablename__='messages'; id:Mapped[int]=mapped_column(primary_key=True); sender_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); recipient_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE')); text:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); read_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
Base.metadata.create_all(engine)

def db():
    with SessionLocal() as s: yield s
def token_for(u:User): return serializer.dumps({'uid':u.id,'email':u.email,'role':u.role})
def current(request:Request,s:Session=Depends(db))->User:
    auth=request.headers.get('Authorization',''); token=auth[7:] if auth.startswith('Bearer ') else request.cookies.get('ss_token')
    if not token: raise HTTPException(401,'Authentication required')
    try: data=serializer.loads(token,max_age=TOKEN_HOURS*3600)
    except (BadSignature,SignatureExpired): raise HTTPException(401,'Invalid or expired session')
    u=s.get(User,data['uid']);
    if not u: raise HTTPException(401,'User not found')
    u.last_seen=now(); s.commit(); return u
def owner(u:User=Depends(current)):
    if u.role!='owner': raise HTTPException(403,'Owner access required')
    return u

def user_out(u:User, followed=False): return {'id':u.id,'email':u.email,'display_name':u.display_name,'phone':u.phone,'qualification':u.qualification,'address':u.address,'bio':u.bio,'avatar':u.avatar,'role':u.role,'presence':u.presence,'last_seen':u.last_seen.isoformat(),'followed':followed,'created_at':u.created_at.isoformat()}
class LoginIn(BaseModel): email:EmailStr; password:str=Field(min_length=4); display_name:str|None=None; auto_create:bool=True
class ProfileIn(BaseModel): display_name:str=Field(min_length=1,max_length=80); phone:str|None=None; qualification:str|None=None; address:str|None=None; bio:str|None=Field(None,max_length=200); avatar:str='S'; presence:str='online'
class TaskIn(BaseModel): title:str=Field(min_length=1,max_length=160); category:str='Work'; priority:str='Medium'; due_date:str|None=None; due_time:str|None=None; duration:int=30; notes:str|None=None; completed:bool=False
class TextIn(BaseModel): text:str=Field(min_length=1,max_length=1000)
class FocusIn(BaseModel): minutes:int=Field(gt=0,le=480); kind:str='focus'; completed:bool=True
class StateIn(BaseModel): payload:dict[str,Any]

app=FastAPI(title="Solomon's Streak API",version='1.0.0',docs_url='/api/docs',redoc_url='/api/redoc')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ALLOWED_ORIGINS','*').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
static=Path(__file__).parent/'static'; app.mount('/static',StaticFiles(directory=static),name='static')
@app.on_event('startup')
def seed_owner():
    with SessionLocal() as s:
        u=s.query(User).filter(User.email==OWNER_EMAIL).first()
        if not u:
            u=User(email=OWNER_EMAIL,password_hash=hash_password(OWNER_PASSWORD),display_name='MD Shafaque',role='owner',bio='Founder and Super Owner',avatar='S²'); s.add(u); s.flush(); s.add(UserState(user_id=u.id,payload='{}')); s.commit()
        elif u.role!='owner': u.role='owner'; u.password_hash=hash_password(OWNER_PASSWORD); s.commit()
@app.get('/api/health')
def health(): return {'status':'ok','time':now().isoformat()}
@app.post('/api/auth/login')
def login(data:LoginIn,s:Session=Depends(db)):
    email=str(data.email).lower(); u=s.query(User).filter(User.email==email).first()
    if not u and data.auto_create and email!=OWNER_EMAIL:
        u=User(email=email,password_hash=hash_password(data.password),display_name=data.display_name or email.split('@')[0]); s.add(u); s.flush(); s.add(UserState(user_id=u.id,payload='{}')); s.commit()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Invalid email or password')
    u.presence='online'; u.last_seen=now(); s.commit(); return {'access_token':token_for(u),'token_type':'bearer','user':user_out(u)}
@app.post('/api/auth/logout')
def logout(u:User=Depends(current),s:Session=Depends(db)): u.presence='offline';u.last_seen=now();s.commit();return {'ok':True}
@app.get('/api/me')
def me(u:User=Depends(current)): return user_out(u)
@app.put('/api/me')
def update_me(data:ProfileIn,u:User=Depends(current),s:Session=Depends(db)):
    for k,v in data.model_dump().items(): setattr(u,k,v)
    s.commit(); return user_out(u)
@app.get('/api/state')
def get_state(u:User=Depends(current),s:Session=Depends(db)): return json.loads((u.state.payload if u.state else '{}') or '{}')
@app.put('/api/state')
def put_state(data:StateIn,u:User=Depends(current),s:Session=Depends(db)):
    if not u.state: u.state=UserState(user_id=u.id)
    u.state.payload=json.dumps(data.payload); s.commit(); return {'ok':True,'updated_at':u.state.updated_at.isoformat()}
@app.get('/api/tasks')
def tasks(u:User=Depends(current),s:Session=Depends(db)): return [task_dict(x) for x in s.query(Task).filter(Task.user_id==u.id).order_by(Task.id.desc())]
def task_dict(x): return {c.name:getattr(x,c.name) for c in x.__table__.columns}
@app.post('/api/tasks')
def create_task(data:TaskIn,u:User=Depends(current),s:Session=Depends(db)): x=Task(user_id=u.id,**data.model_dump());s.add(x);s.commit();return task_dict(x)
@app.put('/api/tasks/{tid}')
def update_task(tid:int,data:TaskIn,u:User=Depends(current),s:Session=Depends(db)):
    x=s.query(Task).filter(Task.id==tid,Task.user_id==u.id).first()
    if not x: raise HTTPException(404,'Task not found')
    for k,v in data.model_dump().items(): setattr(x,k,v)
    s.commit();return task_dict(x)
@app.delete('/api/tasks/{tid}')
def delete_task(tid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.query(Task).filter(Task.id==tid,Task.user_id==u.id).first()
    if not x: raise HTTPException(404,'Task not found')
    s.delete(x);s.commit();return {'ok':True}
@app.post('/api/focus')
def add_focus(data:FocusIn,u:User=Depends(current),s:Session=Depends(db)): x=FocusSession(user_id=u.id,**data.model_dump());s.add(x);s.commit();return {'id':x.id,**data.model_dump()}
@app.get('/api/analytics')
def analytics(u:User=Depends(current),s:Session=Depends(db)):
    total=s.query(Task).filter(Task.user_id==u.id).count();done=s.query(Task).filter(Task.user_id==u.id,Task.completed==True).count();sessions=s.query(FocusSession).filter(FocusSession.user_id==u.id,FocusSession.completed==True).all();mins=sum(x.minutes for x in sessions)
    return {'tasks_total':total,'tasks_completed':done,'completion_rate':round(done/max(total,1)*100),'focus_minutes':mins,'focus_sessions':len(sessions),'momentum':842+done*12+len(sessions)*25}
@app.get('/api/people')
def people(u:User=Depends(current),s:Session=Depends(db)):
    followed={x.following_id for x in s.query(Follow).filter(Follow.follower_id==u.id)}
    return [user_out(x,x.id in followed) for x in s.query(User).filter(User.id!=u.id).order_by(User.presence.desc(),User.display_name)]
@app.post('/api/follows/{uid}')
def toggle_follow(uid:int,u:User=Depends(current),s:Session=Depends(db)):
    if uid==u.id: raise HTTPException(400,'Cannot follow yourself')
    x=s.query(Follow).filter(Follow.follower_id==u.id,Follow.following_id==uid).first()
    if x: s.delete(x);following=False
    else: s.add(Follow(follower_id=u.id,following_id=uid));following=True
    s.commit();return {'following':following}
@app.get('/api/messages/{uid}')
def messages(uid:int,u:User=Depends(current),s:Session=Depends(db)):
    q=s.query(Message).filter(or_((Message.sender_id==u.id)&(Message.recipient_id==uid),(Message.sender_id==uid)&(Message.recipient_id==u.id))).order_by(Message.created_at)
    return [{'id':m.id,'sender_id':m.sender_id,'recipient_id':m.recipient_id,'text':m.text,'created_at':m.created_at.isoformat()} for m in q]
@app.post('/api/messages/{uid}')
def send_message(uid:int,data:TextIn,u:User=Depends(current),s:Session=Depends(db)):
    if not s.get(User,uid): raise HTTPException(404,'Recipient not found')
    m=Message(sender_id=u.id,recipient_id=uid,text=data.text);s.add(m);s.commit();return {'id':m.id,'text':m.text,'created_at':m.created_at.isoformat()}
@app.get('/api/posts')
def posts(u:User=Depends(current),s:Session=Depends(db)):
    return [post_dict(p,u.id,s) for p in s.query(Post).order_by(Post.created_at.desc()).all()]
def post_dict(p,uid,s):
    comments=s.query(Comment).filter(Comment.post_id==p.id).order_by(Comment.created_at).all()
    return {'id':p.id,'text':p.text,'author':user_out(p.author),'created_at':p.created_at.isoformat(),'edited_at':p.edited_at.isoformat() if p.edited_at else None,'liked':any(x.user_id==uid for x in p.likes),'likes':len(p.likes),'comments':[{'id':c.id,'text':c.text,'author':user_out(c.author),'parent_id':c.parent_id,'created_at':c.created_at.isoformat()} for c in comments]}
@app.post('/api/posts')
def create_post(data:TextIn,u:User=Depends(current),s:Session=Depends(db)): p=Post(author_id=u.id,text=data.text);s.add(p);s.commit();return post_dict(p,u.id,s)
@app.put('/api/posts/{pid}')
def edit_post(pid:int,data:TextIn,u:User=Depends(current),s:Session=Depends(db)):
    p=s.get(Post,pid)
    if not p: raise HTTPException(404,'Post not found')
    if p.author_id!=u.id and u.role!='owner': raise HTTPException(403,'Not allowed')
    p.text=data.text;p.edited_at=now();s.commit();return post_dict(p,u.id,s)
@app.delete('/api/posts/{pid}')
def delete_post(pid:int,u:User=Depends(current),s:Session=Depends(db)):
    p=s.get(Post,pid)
    if not p: raise HTTPException(404,'Post not found')
    if p.author_id!=u.id and u.role!='owner': raise HTTPException(403,'Not allowed')
    s.delete(p);s.commit();return {'ok':True}
@app.post('/api/posts/{pid}/like')
def like_post(pid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.query(PostLike).filter(PostLike.post_id==pid,PostLike.user_id==u.id).first()
    if x:s.delete(x);liked=False
    else:s.add(PostLike(post_id=pid,user_id=u.id));liked=True
    s.commit();return {'liked':liked}
@app.post('/api/posts/{pid}/comments')
def comment(pid:int,data:TextIn,parent_id:int|None=None,u:User=Depends(current),s:Session=Depends(db)): c=Comment(post_id=pid,author_id=u.id,parent_id=parent_id,text=data.text);s.add(c);s.commit();return {'id':c.id,'text':c.text}
@app.delete('/api/comments/{cid}')
def delete_comment(cid:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Comment,cid)
    if not c: raise HTTPException(404,'Comment not found')
    if c.author_id!=u.id and u.role!='owner': raise HTTPException(403,'Not allowed')
    s.delete(c);s.commit();return {'ok':True}
@app.get('/api/admin/users')
def admin_users(o:User=Depends(owner),s:Session=Depends(db)): return [user_out(x) for x in s.query(User).all()]
@app.patch('/api/admin/users/{uid}/role')
def admin_role(uid:int,role:str,o:User=Depends(owner),s:Session=Depends(db)):
    u=s.get(User,uid)
    if not u: raise HTTPException(404,'User not found')
    if role not in {'user','moderator','owner'}: raise HTTPException(400,'Invalid role')
    u.role=role;s.commit();return user_out(u)
@app.get('/api/admin/export')
def admin_export(o:User=Depends(owner),s:Session=Depends(db)): return {'users':[user_out(x) for x in s.query(User)],'tasks':s.query(Task).count(),'posts':s.query(Post).count(),'messages':s.query(Message).count()}
class Hub:
    def __init__(self): self.connections:dict[int,WebSocket]={}
    async def connect(self,uid,ws): await ws.accept();self.connections[uid]=ws
    def disconnect(self,uid): self.connections.pop(uid,None)
    async def send(self,uid,data):
        if uid in self.connections: await self.connections[uid].send_json(data)
hub=Hub()
@app.websocket('/api/ws')
async def ws_endpoint(ws:WebSocket,token:str):
    try:data=serializer.loads(token,max_age=TOKEN_HOURS*3600);uid=int(data['uid'])
    except Exception:return await ws.close(code=4401)
    await hub.connect(uid,ws)
    try:
        while True:
            data=await ws.receive_json();rid=int(data['recipient_id']);text=str(data['text'])[:1000]
            with SessionLocal() as s:m=Message(sender_id=uid,recipient_id=rid,text=text);s.add(m);s.commit();mid=m.id;created=m.created_at.isoformat()
            payload={'type':'message','id':mid,'sender_id':uid,'recipient_id':rid,'text':text,'created_at':created};await hub.send(rid,payload);await ws.send_json(payload)
    except WebSocketDisconnect:hub.disconnect(uid)
@app.get('/')
def index(): return FileResponse(static/'index.html')
@app.get('/{path:path}')
def spa(path:str):
    target=static/path
    return FileResponse(target if target.is_file() else static/'index.html')
