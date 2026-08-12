import os, tempfile
fd,path=tempfile.mkstemp(suffix='.db');os.close(fd)
os.environ['DATABASE_URL']='sqlite:///'+path
os.environ['SECRET_KEY']='test-secret'
os.environ['OWNER_EMAIL']='mdshafaque56@gmail.com'
os.environ['OWNER_PASSWORD']='CHANGE_ME_ON_RENDER'
from fastapi.testclient import TestClient
from app.main import app

def auth(token): return {'Authorization':f'Bearer {token}'}
def login(c,email,password,name='Tester'):
    r=c.post('/api/auth/login',json={'email':email,'password':password,'display_name':name,'auto_create':True});assert r.status_code==200,r.text;return r.json()

def test_web_health_user_end_to_end():
    with TestClient(app) as c:
        assert c.get('/').status_code==200
        assert "Solomon's Streak" in c.get('/').text
        assert c.get('/api/health').json()['status']=='ok'
        data=login(c,'user1@example.com','Password123','User One');h=auth(data['access_token'])
        me=c.get('/api/me',headers=h);assert me.status_code==200 and me.json()['role']=='user'
        profile=c.put('/api/me',headers=h,json={'display_name':'User One','phone':'123','qualification':'MBA','address':'Earth','bio':'Builder','avatar':'🚀','presence':'online'});assert profile.status_code==200
        t=c.post('/api/tasks',headers=h,json={'title':'Ship full stack','category':'Work','priority':'High','due_date':'2026-08-12','duration':45,'completed':False});assert t.status_code==200;tid=t.json()['id']
        upd=c.put(f'/api/tasks/{tid}',headers=h,json={'title':'Ship full stack','category':'Work','priority':'High','due_date':'2026-08-12','duration':45,'completed':True});assert upd.json()['completed'] is True
        c.post('/api/focus',headers=h,json={'minutes':25,'kind':'focus','completed':True})
        a=c.get('/api/analytics',headers=h).json();assert a['tasks_completed']==1 and a['focus_minutes']==25
        state={'ss2_theme':'aurora','ss2_tasks':[{'name':'Synced'}]};assert c.put('/api/state',headers=h,json={'payload':state}).status_code==200;assert c.get('/api/state',headers=h).json()==state

def test_discussions_social_and_chat():
    with TestClient(app) as c:
        a=login(c,'a@example.com','Password123','A');b=login(c,'b@example.com','Password123','B');ha,hb=auth(a['access_token']),auth(b['access_token'])
        post=c.post('/api/posts',headers=ha,json={'text':'Hello community'});assert post.status_code==200;pid=post.json()['id']
        like=c.post(f'/api/posts/{pid}/like',headers=hb);assert like.json()['liked'] is True
        com=c.post(f'/api/posts/{pid}/comments',headers=hb,json={'text':'Welcome!'});assert com.status_code==200
        feed=c.get('/api/posts',headers=ha).json();assert feed[0]['likes']==1 and len(feed[0]['comments'])==1
        people=c.get('/api/people',headers=ha).json();bid=next(x['id'] for x in people if x['email']=='b@example.com')
        assert c.post(f'/api/follows/{bid}',headers=ha).json()['following'] is True
        assert c.post(f'/api/messages/{bid}',headers=ha,json={'text':'Hi B 👋'}).status_code==200
        msgs=c.get(f"/api/messages/{a['user']['id']}",headers=hb).json();assert msgs[-1]['text']=='Hi B 👋'

def test_owner_authorization():
    with TestClient(app) as c:
        user=login(c,'normal@example.com','Password123','Normal');hu=auth(user['access_token'])
        assert c.get('/api/admin/users',headers=hu).status_code==403
        owner=login(c,'mdshafaque56@gmail.com','CHANGE_ME_ON_RENDER','Owner');ho=auth(owner['access_token'])
        users=c.get('/api/admin/users',headers=ho);assert users.status_code==200 and len(users.json())>=2
        export=c.get('/api/admin/export',headers=ho);assert export.status_code==200 and 'users' in export.json()
