from sqlalchemy import Boolean, Column, BigInteger, String, ForeignKey, DateTime, Index, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Chatroom(Base, TimestampMixin):
    __tablename__ = "chatrooms"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    
    event = relationship("Event", back_populates="chatrooms")
    manager = relationship("User", foreign_keys=[manager_id])
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship("ChatMessage", back_populates="room", order_by="ChatMessage.created_at", cascade="all, delete-orphan")
    
    
 
    __table_args__ = (
        Index('ix_chatrooms_event_manager_user', 'event_id', 'manager_id', 'user_id', unique=True),
    )
 
    
class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    room_id = Column(BigInteger, ForeignKey("chatrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    
    room = relationship("Chatroom", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    
    
    __table_args__ = (
        Index('ix_chat_messages_sender_recipient', 'sender_id', 'recipient_id'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, room_id={self.room_id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, content='{self.content}', is_read={self.is_read})>"