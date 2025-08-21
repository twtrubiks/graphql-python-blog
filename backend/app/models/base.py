from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declared_attr
from app.core.database import Base


def utc_now():
    """取得當前 UTC 時間（timezone-aware）"""
    return datetime.now(timezone.utc)


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        self.deleted_at = utc_now()
        self.is_deleted = True

    def restore(self):
        self.deleted_at = None
        self.is_deleted = False