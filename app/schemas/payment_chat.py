from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import List, Optional

class PurchasedEventChatItem(BaseModel):
    
    ticket_id: int
    event_id: int
    event_title: str
    event_date: Optional[datetime] = None
    manager_id: int
    manager_name: str
    manager_email: str
    chatroom_id: Optional[int] = None
    quantity: int
    total_price: float
    payment_status: str
    purchases_at: datetime
    

class CustomerChatItem(BaseModel):
    ticket_id: int
    user_id: int
    user_name: str
    user_email: str
    chatroom_id: Optional[int] = None
    quantity: int
    total_price: float
    payment_status: str
    purchases_at: datetime
    


class ManagerEventCustomer(BaseModel):
    event_id: int
    event_title: str
    event_date: Optional[datetime] = None
    customer: List[CustomerChatItem]
    
