from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.models.auth import User
from app.models.event import Event, EventImage
from app.api.deps import get_current_user, require_admin, require_event_manager, require_user_or_manager
from app.schemas.CommonResponse import ApiResponse, PaginatedResponse, PageMeta, BlockRequest
from app.schemas.auth import UserResponse
from app.core.media_handle.cloudinary import delete_image
from app.schemas.event import EventCreate, EventImageOut, EventUpdate, EventOut



def to_event_out(event: Event, images: List[EventImage]) -> EventOut:
    return EventOut(
        id=event.id,
        manager_id=event.manager_id,
        manager_username=event.manager.username if event.manager else None,
        title=event.title,
        description=event.description,
        location=event.location,
        latitude=event.latitude,
        longitude=event.longitude,
        ticket_price=event.ticket_price,
        ticket_limit=event.ticket_limit,
        tickets_sold=event.tickets_sold,
        tickets_available=event.ticket_limit - event.tickets_sold,
        event_date=event.event_date,
        updated_at=event.updated_at,
        is_active=event.is_active,
        created_at=event.created_at,
        images=[{
            "id": image.id,
            "url": image.image_url,
            "public_id": image.cloudinary_public_id
        } for image in images if image.event_id == event.id]
    )



router = APIRouter(prefix='/admin', tags=['Admin'])




@router.get('/users', response_model=ApiResponse[PaginatedResponse[List[UserResponse]]])
def get_users(page: int = Query(1, ge=1), limit: int = Query(10, ge=1), current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    total_users = db.query(User).count()
    if not total_users:
        return ApiResponse(
            success=True,
            statusCode=status.HTTP_200_OK,
            message="No users found",
            data=PaginatedResponse(
                total=0,
                page=page,
                limit=limit,
                items=[]
            )
        )
    offset = (page - 1) * limit
    users = db.query(User).offset(offset).limit(limit).all()
    # print(users)
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_users,
        pages=(total_users + limit - 1) // limit,
        has_next=page * limit < total_users,
        has_previous=page > 1,
    )
    
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Users retrieved successfully",
        data=PaginatedResponse(
            data=[UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_approved=user.is_approved,
                is_verified=user.is_verified,
                is_blocked=user.is_blocked
            ) for user in users],
            
            meta=meta
        )
    )
 
 
 
 
 
@router.get('/users/{user_id}', response_model=ApiResponse[UserResponse])
def get_user_details(user_id: int, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    user_result = db.query(User).filter(User.id == user_id).first()
    if not user_result:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )
    
    user = user_result
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="User details retrieved successfully",
        data=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_approved=user.is_approved,
            is_verified=user.is_verified,
            is_blocked=user.is_blocked
        )
    )  





    
@router.get('/general-users', response_model=ApiResponse[PaginatedResponse[List[UserResponse]]])
def get_general_users(page: int = Query(1, ge=1), limit: int = Query(10, ge=1), current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    total_users = db.query(User).filter(User.role == 'user').count()
    if not total_users:
        return ApiResponse(
            success=True,
            statusCode=status.HTTP_200_OK,
            message="No general users found",
            data=PaginatedResponse(
                total=0,
                page=page,
                limit=limit,
                items=[]
            )
        )
    offset = (page - 1) * limit
    users = db.query(User).filter(User.role == 'user').offset(offset).limit(limit).all()
    
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_users,
        pages=(total_users + limit - 1) // limit,
        has_next=page * limit < total_users,
        has_previous=page > 1,
    )
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="General users retrieved successfully",
        data=PaginatedResponse(
            data=[UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_approved=user.is_approved,
                is_verified=user.is_verified,
                is_blocked=user.is_blocked
            ) for user in users],
            meta=meta
        )
    )
 
 
 
 
    
    
@router.get('/manager-users', response_model=ApiResponse[PaginatedResponse[List[UserResponse]]])
def get_manager_users(page: int = Query(1, ge=1), limit: int = Query(10, ge=1), current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    total_users = db.query(User).filter(User.role == 'manager').count()
    if not total_users:
        return ApiResponse(
            success=True,
            statusCode=status.HTTP_200_OK,
            message="No manager users found",
            data=PaginatedResponse(
                total=0,
                page=page,
                limit=limit,
                items=[]
            )
        )
    offset = (page - 1) * limit
    users = db.query(User).filter(User.role == 'manager').offset(offset).limit(limit).all()
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_users,
        pages=(total_users + limit - 1) // limit,
        has_next=page * limit < total_users,
        has_previous=page > 1,
    )
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Manager users retrieved successfully",
        role='manager',
        data=PaginatedResponse(
            data=[UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                is_approved=user.is_approved,
                is_verified=user.is_verified,
                is_blocked=user.is_blocked
            ) for user in users],
            meta=meta
        )
    )
    
 
 
 
    

@router.patch('/users/{user_id}/block', response_model=ApiResponse[UserResponse])
def block_or_unblock_user(user_id: int, payload: BlockRequest, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    user_result = db.query(User).filter(User.id == user_id).first()
    if not user_result:
        return ApiResponse(
            success= False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None,
            )
        
    if user_result.role == 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Cannot block/unblock an admin user',
            data=None
            )
        
    user = user_result
    user.is_blocked = payload.is_blocked
    db.commit()
    db.refresh(user)
    action = "blocked" if payload.is_blocked else "unblocked"
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message=f"User {action} successfully",
        data=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_approved=user.is_approved,
            is_verified=user.is_verified,
            is_blocked=user.is_blocked
        )
    )
    
    
 
 
 
 
    
@router.delete('/users/{user_id}', response_model=ApiResponse[dict])
def delete_user(user_id: int, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    user_result = db.query(User).filter(User.id == user_id).first()
    if not user_result:
         return ApiResponse(
            success= False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None,
            )
    
    if user_result.role == 'admin':
        return ApiResponse(success=False,
                           statusCode=status.HTTP_403_FORBIDDEN,
                           message='Cannot delete an admin user',
                           data=None,
                           )
    
    user = user_result
    
    # Delete user's events and associated images
    events = db.query(Event).filter(Event.manager_id == user.id).all()
    eimage = db.query(EventImage).filter(EventImage.event_id.in_([event.id for event in events])).all()
    for event in events:
        for image in eimage:
            if image.event_id == event.id:
                delete_image(image.cloudinary_public_id)
        db.delete(event)
    
    db.delete(user)
    db.commit()
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="User and associated events deleted successfully",
        data={"user_id": user_id}
    )
 
 
 
 
 
    
    
@router.get('/events', response_model=ApiResponse[PaginatedResponse[List[EventOut]]])
def get_all_events(page: int = Query(1, ge=1), limit: int = Query(10, ge=1), current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    total_events = db.query(Event).count()
    if not total_events:
        return ApiResponse(
            success=True,
            statusCode=status.HTTP_200_OK,
            message="No events found",
            data=PaginatedResponse(
                total=0,
                page=page,
                limit=limit,
                items=[]
            )
        )
    offset = (page - 1) * limit
    events = db.query(Event).offset(offset).limit(limit).all()
    
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_events,
        pages=(total_events + limit - 1) // limit,
        has_next=page * limit < total_events,
        has_previous=page > 1,
    )
    
    event_outs = []
    for event in events:
        images = db.query(EventImage).filter(EventImage.event_id == event.id).all()
        event_outs.append(to_event_out(event, images))
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Events retrieved successfully",
        data=PaginatedResponse(
            data=event_outs,
            meta=meta
        )
    )
 
 
 
 
 
    

@router.patch('/events/{event_id}', response_model=ApiResponse[EventOut])
def update_event(event_id: int, payload: EventUpdate, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    event_result = db.query(Event).filter(Event.id == event_id).first()
    if not event_result:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='Event not found',
            data=None
        )
    
    event = event_result
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    
    images = db.query(EventImage).filter(EventImage.event_id == event.id).all()
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Event updated successfully",
        data=to_event_out(event, images)
    )
    
  
 
 
 
 
  
    
@router.delete('/events/{event_id}', response_model=ApiResponse[dict])
def delete_event(event_id: int, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    event_result = db.query(Event).filter(Event.id == event_id).first()
    if not event_result:
        return ApiResponse(success=False,
                           statusCode=status.HTTP_404_NOT_FOUND,
                           message="Event not found",
                           data=None
                           )
    
    event = event_result
    
    if event.tickets_sold > 0:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Cannot delete event with sold tickets",
            data=None
        )
    
    eimage = db.query(EventImage).filter(EventImage.event_id == event_id).all()
    for image in eimage:
        try:
            delete_image(image.cloudinary_public_id)
        except Exception as e:
            print(f"Error deleting image {image.cloudinary_public_id}: {str(e)}")
    
    db.delete(event)
    db.commit()
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Event deleted successfully",
        data={"event_id": event_id}
    )
    







@router.get('/stats', response_model=ApiResponse[dict])
def get_stats(current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Admin access required',
            data=None
        )
    total_users = db.query(User).count()
    general_users = db.query(User).filter(User.role == 'user').count()
    manager_users = db.query(User).filter(User.role == 'manager').count()
    total_events = db.query(Event).count()
    sold_events = db.query(Event).filter(Event.tickets_sold > 0).count()
    unsold_events = db.query(Event).filter(Event.tickets_sold == 0).count()
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Platform users statistics retrieved successfully",
        data={
            "total_users": total_users,
            "general_users": general_users,
            "manager_users": manager_users,
            "total_events": total_events,
            "sold_events": sold_events,
            "unsold_events": unsold_events
        }
    )