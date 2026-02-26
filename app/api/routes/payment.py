from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from typing import List
from sqlalchemy.orm import Session, aliased
from sqlmodel import func
import stripe
from datetime import datetime, timedelta, timezone
from app.api.deps import get_current_user, require_user_or_manager, require_admin, require_event_manager
from app.database import get_db
from app.models.ticket import Ticket
from app.models.event import Event
from app.models.auth import User
from app.models.chat import Chatroom, ChatMessage
from app.schemas.CommonResponse import ApiResponse, PaginatedResponse, PageMeta, PaginatedListResponse
from app.schemas.payment_chat import PurchasedEventChatItem, CustomerChatItem, ManagerEventCustomer
from app.schemas.ticket import TicketPurchaseRequest, TicketResponse, CheckoutSessionResponse
from app.core.config import settings



stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter( prefix="/payments", tags=["Payment"] )


@router.post("/checkout", response_model=ApiResponse[CheckoutSessionResponse])
async def create_checkout_session(
    purchase_request: TicketPurchaseRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    
    event = db.query(Event).filter(Event.id == purchase_request.event_id).first()
    if not event:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Event not found",
            data=None
        )
    
    
    available_tickets = event.ticket_limit - event.tickets_sold
    
    if purchase_request.quantity > available_tickets:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=f"Only {available_tickets} tickets available",
            data=None
        )

    total_price = float(event.ticket_price) * purchase_request.quantity
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Tickets for {event.title}",
                        "description": f"Purchase of {purchase_request.quantity} tickets for event '{event.title}'"
                    },
                    "unit_amount": int(float(event.ticket_price) * 100)
                },
                "quantity": purchase_request.quantity,
            }
        ],
        mode="payment",
        success_url=f"{settings.FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/payment-cancel",
        metadata={
            "user_id": current_user['id'],
            "event_id": purchase_request.event_id,
            "quantity": purchase_request.quantity,
            "total_price": total_price
        },
        expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())  # Session expires in 1 hour
    )
    
    ticket = Ticket(
        event_id=purchase_request.event_id,
        user_id=current_user['id'],
        quantity=purchase_request.quantity,
        total_price=total_price,
        purchases_at=datetime.now(timezone.utc),
        stripe_session_id=session.id,
        payment_status="pending"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Checkout session created",
        data=CheckoutSessionResponse(
            session_id=session.id,
            checkout_url=session.url
        )
    )
    
    
    


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
       event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Invalid signature",
            data=None
        )
        
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        payment_intent_id = session.get('payment_intent')
        ticket = db.query(Ticket).filter(Ticket.stripe_session_id == session_id).first()
        if ticket:
            ticket.payment_status = "paid"
            ticket.stripe_payment_intent_id = payment_intent_id
            ticket.purchases_at = datetime.now(timezone.utc)
            event = db.query(Event).filter(Event.id == ticket.event_id).first()
            if event:
                event.tickets_sold += ticket.quantity
            room = db.query(Chatroom).filter(Chatroom.event_id == ticket.event_id, Chatroom.user_id == ticket.user_id).first()
            if not room:
                room = Chatroom(
                    event_id=ticket.event_id,
                    manager_id=event.manager_id,
                    user_id=ticket.user_id
                )
                db.add(room)
            db.commit()
            db.refresh(ticket)
            db.refresh(room)
            
    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        session_id = session.get('id')
        ticket = db.query(Ticket).filter(Ticket.stripe_session_id == session_id).first()
        if ticket and ticket.payment_status == "pending":
            ticket.payment_status = "cancelled"
            db.commit()
            
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Webhook received",
        data=None
    )
    
    
    
    
@router.get("/verify/{session_id}", response_model=ApiResponse[TicketResponse])
def verify_payment(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    ticket = db.query(Ticket).filter(Ticket.stripe_session_id == session_id, Ticket.user_id == current_user['id'], Ticket.payment_status == "paid").first()
    if not ticket:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Ticket not found or payment not completed",
            data=None
        )
     
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    if not event:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Event not found",
            data=None
        )
        
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Ticket verified",
        data=TicketResponse(
            id=ticket.id,
            event_id=ticket.event_id,
            event_title=event.title,
            user_id=ticket.user_id,
            quantity=ticket.quantity,
            total_price=float(ticket.total_price),
            payment_status=ticket.payment_status,
            purchases_at=ticket.purchases_at,
            refund_at=ticket.refund_at
        )
    )
    
    


@router.post("/refund/{ticket_id}", response_model=ApiResponse[dict])
async def refund_ticket(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_404_NOT_FOUND,
            message="Ticket not found",
            data=None
        )
    
    if ticket.payment_status != "paid":
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Only paid tickets can be refunded",
            data=None
        )
    
    now = datetime.now(timezone.utc)
    if ticket.purchases_at and (now - ticket.purchases_at) > timedelta(hours=24):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_400_BAD_REQUEST,
            message="Refund period has expired (24 hours)",
            data=None
        )
    
    try:
        refund = stripe.Refund.create(
            payment_intent=ticket.stripe_payment_intent_id,
            amount=int(ticket.total_price * 100),  # Convert to cents
        )
    except stripe.error.StripeError as e:
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Stripe error: {str(e)}",
            data=None
        )
    ticket.payment_status = "refunded"
    ticket.refund_id = refund.id
    ticket.refund_at = datetime.now(timezone.utc)
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    if event:
        event.tickets_sold = max(0, event.tickets_sold - ticket.quantity)
    db.commit()
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Ticket refunded",
        data={
            "ticket_id": ticket.id,
            "refund_id": refund.id,
            "refund_status": ticket.payment_status
        }
    )
    
    


@router.get("/my-tickets", response_model=ApiResponse[List[TicketResponse]])
async def get_my_tickets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tickets = db.query(Ticket).filter(Ticket.user_id == current_user['id']).all()
    ticket_responses = []
    for ticket in tickets:
        event = db.query(Event).filter(Event.id == ticket.event_id).first()
        if event:
            ticket_responses.append(TicketResponse(
                id=ticket.id,
                event_id=ticket.event_id,
                event_title=event.title,
                user_id=ticket.user_id,
                quantity=ticket.quantity,
                total_price=float(ticket.total_price),
                payment_status=ticket.payment_status,
                purchases_at=ticket.purchases_at,
                refund_at=ticket.refund_at
            ))
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="My tickets retrieved",
        data=ticket_responses
    )
    
    



@router.get("/my-purchased-events", response_model=ApiResponse[PaginatedListResponse[PurchasedEventChatItem]])
async def get_my_purchased_events(
    page: int = Query(1, ge=1),
    limit: int = Query(4, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    Manager = aliased(User)
    
    base_query = (db.query(Ticket, Event, Manager, Chatroom).join(Event, Ticket.event_id == Event.id).join(Manager, Event.manager_id == Manager.id).outerjoin(Chatroom, (Chatroom.event_id == Ticket.event_id) & (Chatroom.user_id == Ticket.user_id)).filter(Ticket.user_id == current_user['id'], Ticket.payment_status == "paid").order_by(Ticket.purchases_at.desc()))
    
    total_count = base_query.count()
    rows = (base_query.offset((page - 1) * limit).limit(limit).all())
    
    results: List[PurchasedEventChatItem] = []
    
    for ticket, event, manager, chatroom in rows:
        if chatroom is None:
            chatroom = Chatroom(
                event_id=event.id,
                manager_id=event.manager_id,
                user_id=ticket.user_id
            )
            db.add(chatroom)
            db.commit()
            db.refresh(chatroom)
            
            
        results.append(PurchasedEventChatItem(
            ticket_id=ticket.id,
            event_id=event.id,
            event_title=event.title,
            event_date=event.event_date,
            manager_id=manager.id,
            manager_name=manager.username,
            manager_email=manager.email,
            chatroom_id=chatroom.id,
            quantity=ticket.quantity,
            total_price=float(ticket.total_price),
            payment_status=ticket.payment_status,
            purchases_at=ticket.purchases_at
        ))
        
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_count,
        pages=(total_count + limit - 1) // limit,
        has_next=page * limit < total_count,
        has_previous=page > 1,
    )
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Purchased events with chatrooms retrieved",
        data=PaginatedListResponse(
            items=results,
            pagination=meta
        )
    )
    
    
    
@router.get("/my-customers", response_model=ApiResponse[PaginatedListResponse[ManagerEventCustomer]])
async def get_my_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(4, ge=1, le=50),
    current_user: dict = Depends(require_event_manager),
    db: Session = Depends(get_db)
):
    UserAlias = aliased(User)
    
    base_query = (db.query(Ticket, Event, UserAlias, Chatroom).join(Ticket, Ticket.event_id == Event.id).join(UserAlias, Ticket.user_id == UserAlias.id).outerjoin(Chatroom, (Chatroom.event_id == Event.id) & (Chatroom.user_id == Ticket.user_id)).filter(Event.manager_id == current_user['id'], Ticket.payment_status == "paid").order_by(Event.event_date.desc(), Ticket.purchases_at.desc()))
    
    total_count = base_query.count()
    rows = base_query.offset((page - 1) * limit).limit(limit).all()
    
    event_customer_map = {}
    
    for ticket, event, user, chatroom in rows:
        if event.id not in event_customer_map:
            event_customer_map[event.id] = {
                "event_id": event.id,
                "event_title": event.title,
                "event_date": event.event_date,
                "customer": []
            }
        
        if chatroom is None:
            chatroom = Chatroom(
                event_id=event.id,
                manager_id=event.manager_id,
                user_id=ticket.user_id
            )
            db.add(chatroom)
            db.commit()
            db.refresh(chatroom)
            
        event_customer_map[event.id]["customer"].append(CustomerChatItem(
            ticket_id=ticket.id,
            user_id=user.id,
            user_name=user.username,
            user_email=user.email,
            chatroom_id=chatroom.id,
            quantity=ticket.quantity,
            total_price=float(ticket.total_price),
            payment_status=ticket.payment_status,
            purchases_at=ticket.purchases_at
        ))
    
    results = [ManagerEventCustomer(**data) for data in event_customer_map.values()]
    
    meta = PageMeta(
        page=page,
        limit=limit,
        total=total_count,
        pages=(total_count + limit - 1) // limit,
        has_next=page * limit < total_count,
        has_previous=page > 1,
    )
    
    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Customers for my events retrieved",
        data=PaginatedListResponse(
            items=results,
            pagination=meta
        )
    )