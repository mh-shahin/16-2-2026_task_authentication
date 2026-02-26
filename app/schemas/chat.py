from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: Optional[int] = None
    sender_name: Optional[str] = None
    content: str
    created_at: datetime
    
    @validator('content')
    def content_length(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Content must be at least 1 character')
        return v.strip()
    
    
    class Config:
        from_attributes = True

    
    
class ChatRoomOut(BaseModel):
    room_id: int
    event_id: int
    event_title: str
    other_user_id: int
    other_username: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    

class MessagePages(BaseModel):
    items: List[MessageOut]
    next_before_id: Optional[int] = None
    has_more: bool = False