from typing import TYPE_CHECKING, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped
from app.models.base import Base
import enum

if TYPE_CHECKING:
    from app.models.tag import Tag


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text, nullable=True)
    status = Column(
        Enum(PostStatus),
        default=PostStatus.DRAFT,
        nullable=False
    )
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    author = relationship("User", back_populates="posts")
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="post_tags",
        back_populates="posts"
    )
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:30] if len(self.title) > 30 else self.title}', status={self.status})>"