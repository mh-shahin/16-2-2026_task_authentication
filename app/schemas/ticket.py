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
    payment_status: str
    purchases_at: Optional[datetime] = None
    refund_at: Optional[datetime] = None
    
    
    class Config:
        from_attributes = True
        
        
        
class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str