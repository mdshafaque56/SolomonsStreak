from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth,users,tasks,progress,chat,discussions
@asynccontextmanager
async def lifespan(app):
    if settings.environment=='development':
        async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
app=FastAPI(title=settings.app_name,version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
for router in (auth.r,users.r,tasks.r,progress.r,chat.r,discussions.r):app.include_router(router,prefix='/api/v1')
@app.get('/health')
async def health():return {'status':'ok'}
