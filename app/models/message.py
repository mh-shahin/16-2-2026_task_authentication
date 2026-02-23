from sqlalchemy import Boolean, Column, BigInteger, String, ForeignKey, DateTime, Index, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    
    
    event = relationship("Event", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    
    __table_args__ = (
        Index('ix_messages_sender_recipient', 'sender_id', 'recipient_id'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, message='{self.message}', sent_at={self.sent_at})>"