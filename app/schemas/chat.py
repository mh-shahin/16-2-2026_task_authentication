from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class MessageCreate(BaseModel):
    event_id: int
    received_id: int
    message : str = Field(..., min_length=1, max_length=1000)
    
    @validator('message')
    def message_length(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Message must be at least 1 character')
        return v.strip()
    


    
    
class MessageResponse(BaseModel):
    id: int
    event_id: int
    sender_id: int
    sender_username: str
    receiver_id: int
    receiver_username: str
    message: str
    sent_at: datetime
    is_read: bool