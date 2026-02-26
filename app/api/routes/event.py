from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status, Form, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, timezone
from decimal import Decimal
from app.database import get_db
from app.api.deps import get_current_user, require_event_manager
from app.schemas.CommonResponse import ApiResponse, PageMeta, PaginatedResponse
from app.schemas.event import EventCreate, EventUpdate, EventOut, EventImageOut
from app.models.event import Event, EventImage
from app.models.auth import User
from app.core.media_handle.cloudinary import upload_image, delete_image

router = APIRouter(prefix="/events", tags=["Events"])


def utcnow():
    return datetime.now(timezone.utc)



def to_event_out(event: Event, manager_username: str, images: List[EventImage]) -> EventOut:
    return EventOut(
        id=event.id,
        manager_id=event.manager_id,
        manager_username=manager_username,
        title=event.title,
        description=event.description,
        location=event.location,
        latitude=event.latitude,
        longitude=event.longitude,
        ticket_price=float(event.ticket_price),
        ticket_limit=event.ticket_limit,
        tickets_sold=event.tickets_sold,
        tickets_available=event.ticket_limit - event.tickets_sold,
        event_date=event.event_date,
        images=[EventImageOut(image_url=i.image_url, cloudinary_public_id=i.cloudinary_public_id) for i in images],
        created_at=event.created_at,
        updated_at=event.updated_at,
        is_active=event.is_active,
    )




@router.post("/create", response_model=ApiResponse[EventOut])
def create_event(
    title: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    ticket_price: float = Form(...),
    ticket_limit: int = Form(...),
    event_date: datetime = Form(...),
    images: List[UploadFile] = File([]),
    
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(images) > 5:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="You can upload a maximum of 5 images per event",
            data=None
        )
        
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )

    if user.role != "manager" or not user.is_approved:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message="Only approved event managers can create events",
            data=None
        )

    now = utcnow()

    new_event = Event(
        manager_id=user.id,
        title=title.strip(),
        description=description.strip(),
        location=location.strip(),
        latitude=latitude,
        longitude=longitude,
        ticket_price=Decimal(str(ticket_price)),
        ticket_limit=ticket_limit,
        tickets_sold=0,
        event_date=event_date,
        created_at=now,
        updated_at=now,
        is_active=True,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    saved_images: List[EventImage] = []
    for idx, image in enumerate(images):
        upload_result = upload_image(image.file, folder="event_images")
        if not upload_result:
            return ApiResponse(
                success=False,
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to upload image",
                data=None
            )

        event_image = EventImage(
            event_id=new_event.id,
            image_url=upload_result["url"],
            cloudinary_public_id=upload_result["public_id"],
            display_order=idx,
            uploaded_at=now,
        )
        db.add(event_image)
        saved_images.append(event_image)

    db.commit()
    
    saved_images = db.query(EventImage).filter(EventImage.event_id == new_event.id).order_by(EventImage.display_order.asc()).all()

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Event created successfully",
        data=to_event_out(new_event, user.username, saved_images),
    )





@router.get("/my-events", response_model=ApiResponse[PaginatedResponse[List[EventOut]]])
def get_my_events(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1, le=50),  
    current_user: dict = Depends(require_event_manager),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )

    if user.role != "manager" or not user.is_approved:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message="Only approved event managers can view their events",
            data=None
        )

    offset = (page - 1) * limit

    base_q = db.query(Event).filter(Event.manager_id == user.id).filter(Event.is_active == True)
    total = base_q.with_entities(func.count(Event.id)).scalar() or 0

    events = (
        base_q.order_by(Event.event_date.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    event_ids = [e.id for e in events]
    images = []
    if event_ids:
        images = db.query(EventImage).filter(EventImage.event_id.in_(event_ids)).order_by(EventImage.display_order.asc()).all()

    # group images by event_id
    img_map: Dict[int, List[EventImage]] = {}
    for img in images:
        img_map.setdefault(img.event_id, []).append(img)

    items = [to_event_out(e, user.username, img_map.get(e.id, [])) for e in events]
    # print(items)
    
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total,
        pages=(total + limit - 1) // limit,
        has_next=page * limit < total,
        has_previous=page > 1,
    )

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Events retrieved successfully",
        data= PaginatedResponse(
            data=items,
            meta=meta,
        ),
    )





@router.get("/", response_model=ApiResponse[PaginatedResponse[List[EventOut]]])
def get_events(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    base_q = db.query(Event).filter(Event.is_active == True)
    total = base_q.with_entities(func.count(Event.id)).scalar() or 0

    events = (
        base_q.order_by(Event.event_date.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    event_ids = [e.id for e in events]
    images = []
    managers = {}
    if event_ids:
        images = db.query(EventImage).filter(EventImage.event_id.in_(event_ids)).order_by(EventImage.display_order.asc()).all()

        manager_ids = list({e.manager_id for e in events})
        users = db.query(User).filter(User.id.in_(manager_ids)).all()
        managers = {u.id: u.username for u in users}

    img_map: Dict[int, List[EventImage]] = {}
    for img in images:
        img_map.setdefault(img.event_id, []).append(img)

    items = [to_event_out(e, managers.get(e.manager_id, "unknown"), img_map.get(e.id, [])) for e in events]
    
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total,
        pages=(total + limit - 1) // limit,
        has_next=page * limit < total,
        has_previous=page > 1,
    )

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Events retrieved successfully",
        data=PaginatedResponse(data = items, meta=meta),
    )






@router.get("/{event_id}", response_model=ApiResponse[EventOut])
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id, Event.is_active == True).first()
    if not event:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Event not found",
            data=None
        )

    manager = db.query(User).filter(User.id == event.manager_id).first()
    images = db.query(EventImage).filter(EventImage.event_id == event.id).order_by(EventImage.display_order.asc()).all()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Event retrieved successfully",
        data=to_event_out(event, manager.username if manager else "unknown", images),
    )






@router.patch("/{event_id}", response_model=ApiResponse[EventOut])
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: dict = Depends(require_event_manager),
    db: Session = Depends(get_db),
):
    
    user_data = db.query(User).filter(User.id == current_user["id"]).first()
    print(f"User data from DB: {user_data}")

    if user_data.role != 'manager':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Only approved event managers can update events',
            data=None
        )
    event = db.query(Event).filter(Event.id == event_id, Event.is_active == True).first()
    if not event:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='Event not found',
            data=None
        )

    if event.manager_id != user_data.id:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='You can only update your own events',
            data=None
        )

    # update fields
    if event_update.title is not None:
        event.title = event_update.title
    if event_update.description is not None:
        event.description = event_update.description
    if event_update.location is not None:
        event.location = event_update.location
    if event_update.latitude is not None:
        event.latitude = event_update.latitude
    if event_update.longitude is not None:
        event.longitude = event_update.longitude
    if event_update.ticket_limit is not None:
        if event_update.ticket_limit < event.tickets_sold:
            return ApiResponse(
                success=False,
                statusCode=status.HTTP_400_BAD_REQUEST,
                message='Ticket limit cannot be less than tickets already sold',
                data=None
            )
        event.ticket_limit = event_update.ticket_limit
    if event_update.event_date is not None:
        if event_update.event_date <= utcnow():
            return ApiResponse(
                success=False,
                statusCode=status.HTTP_400_BAD_REQUEST,
                message='Event date must be in the future',
                data=None
            )
        event.event_date = event_update.event_date

    event.updated_at = utcnow()
    db.commit()
    db.refresh(event)

    manager = db.query(User).filter(User.id == event.manager_id).first()
    images = db.query(EventImage).filter(EventImage.event_id == event.id).order_by(EventImage.display_order.asc()).all()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Event updated successfully",
        data=to_event_out(event, manager.username if manager else "unknown", images),
    )







@router.delete("/{event_id}", response_model=ApiResponse[dict])
def delete_event(
    event_id: int,
    current_user: dict = Depends(require_event_manager),
    db: Session = Depends(get_db),
):
    user_data = db.query(User).filter(User.id == current_user["id"]).first()
    if user_data.role != 'manager':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Only approved event managers can delete events',
            data=None
            )
        
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='Event not found',
            data=None
        )

    if event.manager_id != user_data.id:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='You can only delete your own events',
            data=None
        )

    if event.tickets_sold > 0:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='Cannot delete event with sold tickets',
            data=None
        )

    images = db.query(EventImage).filter(EventImage.event_id == event_id).all()

    for img in images:
        try:
            delete_image(img.cloudinary_public_id)
        except Exception:
            pass  

    db.delete(event)
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Event deleted successfully",
        data={"event_id": event_id},
    )