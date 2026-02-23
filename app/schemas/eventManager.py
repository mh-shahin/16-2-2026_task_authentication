from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal
from datetime import datetime


class ManagerRequestResponse(BaseModel):
    id: int
    user_id: int
    username: str
    email: EmailStr
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    
 
 
 
    
class ManagerReviewRequest(BaseModel):
    status: Literal['approved', 'rejected']
    

