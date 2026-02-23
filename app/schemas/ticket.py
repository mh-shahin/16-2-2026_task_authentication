from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class TicketPurchaseRequest(BaseModel):
    event_id: int
    quantity: int = 1
    
    @validator('quantity')
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be a positive integer')
        return v
    
    
class TicketResponse(BaseModel):
    id: int
    event_id: int
    event_title: str
    user_id: int
    quantity: int
    total_price: float
    purchase_date: datetime