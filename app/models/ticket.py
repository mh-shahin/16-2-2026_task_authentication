from sqlalchemy import CheckConstraint, Column, DateTime, BigInteger, String, ForeignKey, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin



class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity = Column(BigInteger, nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    purchases_at = Column(DateTime(timezone=True), nullable=False)
    
    stripe_session_id = Column(String, unique=True, nullable=True, index=True)
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    payment_status = Column(String, default="pending", nullable=True, index=True)
    
    refund_id = Column(String, unique=True, nullable=True, index=True)
    refund_at = Column(DateTime(timezone=True), nullable=True)
    
    
    
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_ticket_quantity_positive'),
        CheckConstraint('total_price > 0', name='check_ticket_total_price_positive'),
        Index("uq_event_user_active_ticket", "event_id", "user_id", unique=True, postgresql_where=(refund_at.is_(None) & (payment_status.in_(["paid", "succeeded"])))),
    )
    
    event = relationship("Event", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    def __repr__(self):
        return f"<Ticket(id={self.id}, event_id={self.event_id}, user_id={self.user_id}, quantity={self.quantity}, total_price={self.total_price}, payment_status={self.payment_status})>"