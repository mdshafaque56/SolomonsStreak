import uuid, enum
from datetime import datetime, date
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Date, ForeignKey, UniqueConstraint, Index, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
class Base(DeclarativeBase): pass
class Priority(str,enum.Enum): low="Low"; medium="Medium"; high="High"
class Presence(str,enum.Enum): online="online"; away="away"; busy="busy"; offline="offline"
class User(Base):
    __tablename__='users'
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    email: Mapped[str]=mapped_column(String(320),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(Text)
    display_name: Mapped[str]=mapped_column(String(80),index=True)
    avatar: Mapped[str]=mapped_column(String(20),default='S')
    bio: Mapped[str|None]=mapped_column(String(160))
    phone: Mapped[str|None]=mapped_column(String(30))
    qualification: Mapped[str|None]=mapped_column(String(160))
    address: Mapped[str|None]=mapped_column(String(300))
    timezone: Mapped[str]=mapped_column(String(64),default='UTC')
    presence: Mapped[Presence]=mapped_column(Enum(Presence),default=Presence.offline,index=True)
    last_seen: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class UserStats(Base):
    __tablename__='user_stats'
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    score: Mapped[int]=mapped_column(Integer,default=0)
    current_streak: Mapped[int]=mapped_column(Integer,default=0)
    longest_streak: Mapped[int]=mapped_column(Integer,default=0)
    last_active_date: Mapped[date|None]=mapped_column(Date)
    completed_tasks: Mapped[int]=mapped_column(Integer,default=0)
    focus_minutes: Mapped[int]=mapped_column(Integer,default=0)
    focus_sessions: Mapped[int]=mapped_column(Integer,default=0)
class Task(Base):
    __tablename__='tasks'; __table_args__=(Index('ix_tasks_owner_date','owner_id','task_date'),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    title: Mapped[str]=mapped_column(String(255)); category: Mapped[str]=mapped_column(String(40),default='Personal')
    priority: Mapped[Priority]=mapped_column(Enum(Priority),default=Priority.medium)
    task_date: Mapped[date]=mapped_column(Date,index=True)
    completed: Mapped[bool]=mapped_column(Boolean,default=False); completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class FocusSession(Base):
    __tablename__='focus_sessions'
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    minutes: Mapped[int]=mapped_column(Integer); completed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class Follow(Base):
    __tablename__='follows'; __table_args__=(UniqueConstraint('follower_id','following_id'),)
    follower_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    following_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class Conversation(Base):
    __tablename__='conversations'
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    direct_key: Mapped[str]=mapped_column(String(73),unique=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class ConversationMember(Base):
    __tablename__='conversation_members'; __table_args__=(UniqueConstraint('conversation_id','user_id'),)
    conversation_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('conversations.id',ondelete='CASCADE'),primary_key=True)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    last_read_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class Message(Base):
    __tablename__='messages'; __table_args__=(Index('ix_messages_conversation_created','conversation_id','created_at'),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('conversations.id',ondelete='CASCADE'),index=True)
    sender_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    content: Mapped[str]=mapped_column(String(1000)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class Post(Base):
    __tablename__='posts'; __table_args__=(Index('ix_posts_created','created_at'),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    author_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    content: Mapped[str]=mapped_column(String(1000)); edited: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
class PostLike(Base):
    __tablename__='post_likes'
    post_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE'),primary_key=True)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
class Comment(Base):
    __tablename__='comments'; __table_args__=(Index('ix_comments_post_created','post_id','created_at'),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    post_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('posts.id',ondelete='CASCADE'),index=True)
    author_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    parent_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey('comments.id',ondelete='CASCADE'))
    content: Mapped[str]=mapped_column(String(500)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class RefreshToken(Base):
    __tablename__='refresh_tokens'
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True); expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); revoked: Mapped[bool]=mapped_column(Boolean,default=False)
