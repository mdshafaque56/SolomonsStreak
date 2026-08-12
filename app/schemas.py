import uuid
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
class Register(BaseModel):
    email: EmailStr; password: str=Field(min_length=8,max_length=128); display_name: str=Field(min_length=2,max_length=80); timezone: str='UTC'
class Login(BaseModel): email: EmailStr; password: str
class TokenPair(BaseModel): access_token:str; refresh_token:str; token_type:str='bearer'
class ProfileUpdate(BaseModel):
    display_name:str|None=Field(None,min_length=2,max_length=80); avatar:str|None=None; bio:str|None=Field(None,max_length=160); phone:str|None=None; qualification:str|None=None; address:str|None=None; timezone:str|None=None
class TaskIn(BaseModel):
    title:str=Field(min_length=1,max_length=255); category:str='Personal'; priority:str='Medium'; task_date:date
class FocusIn(BaseModel): minutes:int=Field(ge=1,le=240)
class TextIn(BaseModel): content:str=Field(min_length=1,max_length=1000)
class CommentIn(BaseModel): content:str=Field(min_length=1,max_length=500); parent_id:uuid.UUID|None=None
