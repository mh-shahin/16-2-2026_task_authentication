from sqlalchemy import Column, DateTime, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class EventManager(Base, TimestampMixin):
    __tablename__ = "event_managers"
    
    id = Column(BigInteger, primary_key=True, unique=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String, default="pending", nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    
    user = relationship("User", foreign_keys=[user_id], back_populates="event_manager", uselist=False)
    reviewer = relationship("User", foreign_keys=[reviewed_by], uselist=False)
    
    
    def __repr__(self):
        return f"<EventManager(id={self.id}, user_id={self.user_id}, status='{self.status}')>"