from dataclasses import Field
from sqlalchemy import Boolean, CheckConstraint, Column, BigInteger, DateTime, Numeric, String, ForeignKey, Text
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from fastapi import UploadFile

class Event(Base, TimestampMixin):
    __tablename__ = "events"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    manager_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=False, index=True)
    latitude = Column(Numeric(precision=10, scale=8), nullable=True)
    longitude = Column(Numeric(precision=11, scale=8), nullable=True)
    ticket_price = Column(Numeric(precision=10, scale=2), nullable=False)
    ticket_limit = Column(BigInteger, nullable=False)
    tickets_sold = Column(BigInteger, default=0, nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)    
    
    
    __table_args__ = (
        CheckConstraint('event_date > created_at', name='check_event_date_future'),
        CheckConstraint('ticket_price > 0', name='check_ticket_price_positive'),
        CheckConstraint('ticket_limit > 0', name='check_ticket_limit_positive'),
        CheckConstraint('tickets_sold >= 0', name='check_tickets_sold_non_negative'),
        CheckConstraint('tickets_sold <= ticket_limit', name='check_tickets_sold_within_limit')
    )
    
    
    manager = relationship("User", back_populates="events")
    images = relationship("EventImage", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event", cascade="all, delete-orphan")
    chatrooms = relationship("Chatroom", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', manager_id={self.manager_id})>"
    
    
    
class EventImage(Base, TimestampMixin):
    __tablename__ = "event_images"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String, nullable=False)
    cloudinary_public_id = Column(String, nullable=False)
    display_order = Column(BigInteger, nullable=False, default=0)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    event = relationship("Event", back_populates="images")
    
    def __repr__(self):
        return f"<EventImage(id={self.id}, event_id={self.event_id})>"