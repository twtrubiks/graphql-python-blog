"""追蹤關係模型"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, DateTime, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Follow(Base):
    """追蹤關係模型"""
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    followed_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 關聯
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following_relationships")
    followed = relationship("User", foreign_keys=[followed_id], back_populates="follower_relationships")
    
    # 約束
    __table_args__ = (
        UniqueConstraint('follower_id', 'followed_id', name='uq_follower_followed'),
        CheckConstraint('follower_id != followed_id', name='check_no_self_follow'),
    )