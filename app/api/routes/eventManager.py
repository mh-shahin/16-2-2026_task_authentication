from fastapi import APIRouter, Depends, status
from sentry_sdk.utils import now
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from app.database import get_db
from app.schemas.eventManager import ManagerRequestResponse, ManagerReviewRequest
from app.schemas.CommonResponse import ApiResponse
from app.models.eventManager import EventManager
from app.models.auth import User
from app.api.deps import get_current_user, require_admin


now = datetime.now(timezone.utc)

router = APIRouter(prefix='/request', tags=['Manager Requests'])



@router.post('/manager-request', response_model=ApiResponse[ManagerRequestResponse])
def create_manager_request(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_result = db.query(User).filter(User.id == current_user['id']).first()
    
    if not user_result:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )
    
    user = user_result
    
    if user.role == 'manager' and user.is_approved:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="You are already approved as a event manager",
            data=None
        )
    
    existing_request = db.query(EventManager).filter(EventManager.user_id == user.id).first()
    
    if existing_request:
        if existing_request.status == 'pending':
            return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="You already have a pending manager request",
            data=None
        )
        elif existing_request.status == 'approved':
            return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="You are already approved as a event manager",
            data=None
            )
        elif existing_request.status == 'rejected':
                existing_request.status = 'pending'
                existing_request.requested_at = now
                existing_request.reviewed_at = None
                existing_request.reviewed_by = None
                db.commit()
                db.refresh(existing_request)
                return ApiResponse(
                    success=True,
                    statusCode=status.HTTP_200_OK,
                    message="Manager rejected request resubmitted successfully",
                    data=ManagerRequestResponse(
                        id=existing_request.id,
                        user_id=user.id,
                        username=user.username,
                        email=user.email,
                        status='pending',
                        requested_at=existing_request.requested_at,
                        reviewed_at=existing_request.reviewed_at,
                    )
                )
                    
                     
    new_request = EventManager(
        user_id=user.id,
        status='pending',
        requested_at=now,
        reviewed_at=None,
        reviewed_by=None
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_201_CREATED,
        message="Manager request created successfully",
        data=ManagerRequestResponse(
            id=new_request.id,
            user_id=user.id,
            username=user.username,
            email=user.email,
            status='pending',
            requested_at=new_request.requested_at,
            reviewed_at=new_request.reviewed_at,
        )
    )
    





    
    
@router.get('/my-request', response_model=ApiResponse[dict])
def get_my_request(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_result = db.query(User).filter(User.id == current_user['id']).first()
    if not user_result:
        return ApiResponse(
            success= False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="User not found",
            data=None,
        )
    
    user = user_result
    manager_request = db.query(EventManager).filter(EventManager.user_id == user.id).first()
    
    if not manager_request:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="No manager request found for this user",
            data=None
            )
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Manager request retrieved successfully",
        data={
            "id": manager_request.id,
            "user_id": manager_request.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "status": manager_request.status,
            "requested_at": manager_request.requested_at,
            "reviewed_at": manager_request.reviewed_at,
        }
    )
    









@router.get('/all-requests', response_model=ApiResponse[List[ManagerRequestResponse]])
def get_all_requests(current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Only admins can view all manager requests',
            data=None
        )
    requests = db.query(EventManager).all()
    response_data = []
    for req in requests:
        user_result = db.query(User).filter(User.id == req.user_id).first()
        if user_result:
            user = user_result
            response_data.append(ManagerRequestResponse(
                id=req.id,
                user_id=req.user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                status=req.status,
                requested_at=req.requested_at,
                reviewed_at=req.reviewed_at,
            ))
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="All manager requests retrieved successfully",
        data=response_data
    )







    
@router.get('/pending-requests', response_model=ApiResponse[List[ManagerRequestResponse]])
def get_pending_requests(current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Only admins can view pending manager requests',
            data=None
        )
        
    pending_requests = db.query(EventManager).filter(EventManager.status == 'pending').all()
    response_data = []
    for req in pending_requests:
        user_result = db.query(User).filter(User.id == req.user_id).first()
        if user_result:
            user = user_result
            response_data.append(ManagerRequestResponse(
                id=req.id,
                user_id=req.user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                status=req.status,
                requested_at=req.requested_at,
                reviewed_at=req.reviewed_at,
            ))
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Pending manager requests retrieved successfully",
        data=response_data
    )
    








@router.patch('/{request_id}', response_model=ApiResponse[dict])
def update_manager_request(request_id: int, review: ManagerReviewRequest, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)):
    
    if current_user['role'] != 'admin':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message='Only admins can review manager requests',
            data=None
        )
    
    manager_request_result = db.query(EventManager).filter(EventManager.id == request_id).first()
    
    if not manager_request_result:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='Manager request not found',
            data=None
        )
    
    manager_request = manager_request_result
    
    if manager_request.status != 'pending':
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message='Only pending requests can be updated',
            data=None
        )
    
    user_result = db.query(User).filter(User.id == manager_request.user_id).first()
    if not user_result:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message='User not found',
            data=None
        )
    
    user = user_result
    
    if review.status == 'approved':
        user.role = 'manager'
        user.is_approved = True
        db.query(User).filter(User.id == user.id).update({
            User.role: user.role,
            User.is_approved: user.is_approved,
        })
    
    manager_request.status = review.status
    manager_request.reviewed_at = datetime.utcnow()
    manager_request.reviewed_by = current_user['id']
    
    db.commit()
    db.refresh(manager_request)
    db.refresh(user)
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message=f"Manager request {review.status} successfully",
        data={
            "request_id": manager_request.id,
            "user_id": manager_request.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "status": manager_request.status,
            "requested_at": manager_request.requested_at,
            "reviewed_at": manager_request.reviewed_at,
        }
    )