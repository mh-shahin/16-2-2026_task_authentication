from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    statusCode: int
    message: str
    data: Optional[T] = None





class PageMeta(BaseModel):
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_previous: bool




    
    
class PaginatedResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: Optional[PageMeta] = None
    
 
 
 
    
class BlockRequest(BaseModel):
    is_blocked: bool
    