from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
import json
from app.models.ticket import Ticket
from app.core.config import settings
from app.database import SessionLocal, get_db
from app.api.deps import get_current_user  
from app.models.chat import Chatroom, ChatMessage
from app.schemas.chat import ChatRoomOut, MessageOut, MessagePages
from app.schemas.CommonResponse import ApiResponse


router = APIRouter(prefix="/chat", tags=["Chat"])



async def ws_error(
    websocket: WebSocket,
    *,
    http_status: int,
    message: str,
    close_code: int = 1008
) -> None:

    try:
        await websocket.send_text(json.dumps({
            "success": False,
            "statusCode": http_status,
            "message": message,
            "data": None
        }))
    finally:
        await websocket.close(code=close_code)




def has_active_ticket(db: Session, user_id: int, event_id: int) -> bool:

    ticket = (
        db.query(Ticket)
        .filter(
            Ticket.user_id == user_id,
            Ticket.event_id == event_id,
            Ticket.refund_at.is_(None),
            Ticket.refund_id.is_(None),
            Ticket.payment_status=="paid" 
        )
        .first()
    )
    return ticket is not None







class ConnectionManager:

    def __init__(self):
        self.active: Dict[int, List[Tuple[int, WebSocket]]] = {}

    async def connect(self, room_id: int, user_id: int, websocket: WebSocket) -> None:

        self.active.setdefault(room_id, []).append((user_id, websocket))

    def disconnect(self, room_id: int, user_id: int, websocket: WebSocket) -> None:

        if room_id not in self.active:
            return

        self.active[room_id] = [
            (uid, ws) for (uid, ws) in self.active[room_id]
            if not (uid == user_id and ws == websocket)
        ]

        if not self.active[room_id]:
            del self.active[room_id]

    async def broadcast(self, room_id: int, message: dict) -> None:

        dead: List[Tuple[int, WebSocket]] = []

        for uid, ws in self.active.get(room_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append((uid, ws))

        for uid, ws in dead:
            self.disconnect(room_id, uid, ws)


manager = ConnectionManager()




        


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str = Query(None)):

    await websocket.accept()


    if not token:
        await ws_error(
            websocket,
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Token required"
        )
        return

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            await ws_error(
                websocket,
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Token missing user_id"
            )
            return
    except JWTError:
        await ws_error(
            websocket,
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid token"
        )
        return


    db: Session = SessionLocal()
    try:
        chatroom = db.query(Chatroom).filter(Chatroom.id == room_id).first()
        if not chatroom:
            await ws_error(
                websocket,
                http_status=status.HTTP_404_NOT_FOUND,
                message="Chat room not found"
            )
            return
        
        if user_id == chatroom.manager_id:
            pass
        
        elif user_id == chatroom.user_id:
            if not has_active_ticket(db, user_id, chatroom.event_id):
                await ws_error(
                    websocket,
                    http_status=status.HTTP_403_FORBIDDEN,
                    message="No active ticket for this event"
                )
                return
            
        else:
            await ws_error(
                websocket,
                http_status=status.HTTP_403_FORBIDDEN,
                message="Your are not a participant in this chat room"
            )
            return
        
        
        await manager.connect(room_id, user_id, websocket)


        while True:
            raw = await websocket.receive_text()

            try:
                obj = json.loads(raw)
                content = (obj.get("content") or "").strip()
            except Exception:
                content = raw.strip()

            if not content:
                continue

            recipient_id = chatroom.manager_id if user_id == chatroom.user_id else chatroom.user_id

            new_message = ChatMessage(
                room_id=room_id,
                sender_id=user_id,
                recipient_id=recipient_id,
                content=content,
                is_read=False
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            await manager.broadcast(room_id, {
                "success": True,
                "statusCode": status.HTTP_200_OK,
                "message": "New message",
                "data": {
                    "id": new_message.id,
                    "room_id": new_message.room_id,
                    "sender_id": new_message.sender_id,
                    "recipient_id": new_message.recipient_id,
                    "content": new_message.content,
                    "created_at": new_message.created_at.isoformat()
                }
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws_error(
                websocket,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Server error: {str(e)}",
                close_code=1011
            )
        except Exception:
            pass
    finally:
        manager.disconnect(room_id, user_id, websocket)
        db.close()





@router.get("/rooms", response_model=ApiResponse[List[ChatRoomOut]])
async def get_chat_rooms(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user["id"]

    chatrooms = db.query(Chatroom).filter(
        (Chatroom.user_id == user_id) | (Chatroom.manager_id == user_id)
    ).all()

    rooms_out: List[ChatRoomOut] = []
    for room in chatrooms:
        other_user = room.manager if room.user_id == user_id else room.user

        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.room_id == room.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        rooms_out.append(ChatRoomOut(
            room_id=room.id,
            event_id=room.event_id,
            event_title=room.event.title,
            other_user_id=other_user.id,
            other_username=other_user.username,
            last_message=last_message.content if last_message else None,
            last_message_time=last_message.created_at if last_message else None
        ))

    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Chat rooms retrieved successfully",
        data=rooms_out
    )



@router.get("/rooms/{room_id}/messages", response_model=ApiResponse[MessagePages])
async def get_chat_messages(
    room_id: int,
    before_id: Optional[int] = Query(None, description="Load messages with id < before_id"),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user["id"]

    chatroom = db.query(Chatroom).filter(Chatroom.id == room_id).first()
    print(f"Chatroom: {chatroom}")
    if not chatroom or (chatroom.user_id != user_id and chatroom.manager_id != user_id):
        return ApiResponse(
            success=False,
            statusCode=status.HTTP_403_FORBIDDEN,
            message="Not allowed to view messages in this room",
            data=None
        )

    q = db.query(ChatMessage).filter(ChatMessage.room_id == room_id)

    if before_id is not None:
        q = q.filter(ChatMessage.id < before_id)

    rows = (
        q.order_by(ChatMessage.id.desc())
         .limit(limit + 1)  
         .all()
    )

    has_more = len(rows) > limit
    rows = rows[:limit]

    rows.reverse()

    items = []
    for m in rows:
        item = MessageOut(
            id = m.id,
            room_id=m.room_id,
            sender_id=m.sender_id,
            sender_name=m.sender.username if m.sender else None,
            content=m.content,
            created_at=m.created_at,
        )
        items.append(item)
    
    print(f"Items: {items}")
    next_before_id = rows[0].id if has_more and rows else None

    return ApiResponse(
        success=True,
        statusCode=status.HTTP_200_OK,
        message="Messages retrieved successfully",
        data=MessagePages(
            items=items,
            next_before_id=next_before_id,
            has_more=has_more
        )
    )
    
    
