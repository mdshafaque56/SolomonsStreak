from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Post,PostLike,Comment,User
from app.schemas import TextIn,CommentIn
from app.security import current_user
r=APIRouter(prefix='/discussions',tags=['discussions'])
@r.get('')
async def feed(sort:str='new',limit:int=Query(30,le=100),offset:int=0,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    likes=select(PostLike.post_id,func.count().label('likes')).group_by(PostLike.post_id).subquery(); comments=select(Comment.post_id,func.count().label('comments')).group_by(Comment.post_id).subquery()
    q=select(Post,User.display_name,User.avatar,func.coalesce(likes.c.likes,0),func.coalesce(comments.c.comments,0)).join(User,User.id==Post.author_id).outerjoin(likes,likes.c.post_id==Post.id).outerjoin(comments,comments.c.post_id==Post.id)
    order=func.coalesce(likes.c.likes,0).desc() if sort=='popular' else func.coalesce(comments.c.comments,0).desc() if sort=='active' else Post.created_at.desc()
    rows=(await db.execute(q.order_by(order).limit(limit).offset(offset))).all(); return [{'post':p,'author':n,'avatar':a,'likes':lc,'comments':cc} for p,n,a,lc,cc in rows]
@r.post('',status_code=201)
async def create(x:TextIn,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    p=Post(author_id=u.id,content=x.content.strip());db.add(p);await db.commit();await db.refresh(p);return p
@r.patch('/{post_id}')
async def edit(post_id:str,x:TextIn,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(Post).where(Post.id==post_id,Post.author_id==u.id));
    if not p:raise HTTPException(404,'Post not found')
    p.content=x.content.strip();p.edited=True;await db.commit();return p
@r.delete('/{post_id}',status_code=204)
async def delete(post_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(Post).where(Post.id==post_id,Post.author_id==u.id));
    if not p:raise HTTPException(404,'Post not found')
    await db.delete(p);await db.commit()
@r.put('/{post_id}/like',status_code=204)
async def like(post_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if not await db.get(Post,post_id):raise HTTPException(404,'Post not found')
    if not await db.scalar(select(PostLike).where(PostLike.post_id==post_id,PostLike.user_id==u.id)):db.add(PostLike(post_id=post_id,user_id=u.id));await db.commit()
@r.delete('/{post_id}/like',status_code=204)
async def unlike(post_id:str,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    x=await db.scalar(select(PostLike).where(PostLike.post_id==post_id,PostLike.user_id==u.id));
    if x:await db.delete(x);await db.commit()
@r.post('/{post_id}/comments',status_code=201)
async def comment(post_id:str,x:CommentIn,u=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if not await db.get(Post,post_id):raise HTTPException(404,'Post not found')
    if x.parent_id:
        parent=await db.get(Comment,x.parent_id)
        if not parent or str(parent.post_id)!=post_id:raise HTTPException(422,'Invalid parent comment')
    c=Comment(post_id=post_id,author_id=u.id,parent_id=x.parent_id,content=x.content.strip());db.add(c);await db.commit();await db.refresh(c);return c
