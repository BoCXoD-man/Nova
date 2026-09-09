from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    preferred_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="ru",
    )

    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    timezone: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    birth_date: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    telegram_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    telegram_username: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    telegram_profile_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    facts: Mapped[list["UserFact"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    related_people: Mapped[list["RelatedPerson"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<User("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"preferred_name={self.preferred_name!r}"
            f")>"
        )


class UserFact(Base):
    __tablename__ = "user_facts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="facts",
    )

    __table_args__ = (
        Index(
            "ix_user_facts_user_id",
            "user_id",
        ),
        Index(
            "ix_user_facts_category_key",
            "category",
            "key",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserFact("
            f"id={self.id}, "
            f"category={self.category!r}, "
            f"key={self.key!r}, "
            f"value={self.value!r}"
            f")>"
        )


class RelatedPerson(Base):
    __tablename__ = "related_people"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    preferred_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="related_people",
    )

    relations: Mapped[list["Relation"]] = relationship(
        back_populates="related_person",
        cascade="all, delete-orphan",
    )

    facts: Mapped[list["PersonFact"]] = relationship(
        back_populates="related_person",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<RelatedPerson("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"preferred_name={self.preferred_name!r}"
            f")>"
        )


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    related_person_id: Mapped[int] = mapped_column(
        ForeignKey(
            "related_people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    relation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    related_person: Mapped["RelatedPerson"] = relationship(
        back_populates="relations",
    )

    __table_args__ = (
        Index(
            "ix_relations_user_id",
            "user_id",
        ),
        Index(
            "ix_relations_related_person_id",
            "related_person_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Relation("
            f"id={self.id}, "
            f"type={self.relation_type!r}, "
            f"person_id={self.related_person_id}"
            f")>"
        )


class PersonFact(Base):
    __tablename__ = "person_facts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    related_person_id: Mapped[int] = mapped_column(
        ForeignKey(
            "related_people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    related_person: Mapped["RelatedPerson"] = relationship(
        back_populates="facts",
    )

    __table_args__ = (
        Index(
            "ix_person_facts_person_id",
            "related_person_id",
        ),
        Index(
            "ix_person_facts_category_key",
            "category",
            "key",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PersonFact("
            f"id={self.id}, "
            f"category={self.category!r}, "
            f"key={self.key!r}, "
            f"value={self.value!r}"
            f")>"
        )