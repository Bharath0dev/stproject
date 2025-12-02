from uuid import uuid4
from sqlalchemy import Column, String, DateTime, LargeBinary, UniqueConstraint, Integer, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    categories = relationship("PersonalCategory", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("PersonalExpense", back_populates="user", cascade="all, delete-orphan")


class PersonalCategory(Base):
    __tablename__ = "personal_categories"
    __table_args__ = (
        UniqueConstraint('user_id', 'name', 'type', name='uq_user_category'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'income' or 'expense'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="categories")
    expenses = relationship("PersonalExpense", back_populates="category")


class PersonalExpense(Base):
    __tablename__ = "personal_expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("personal_categories.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="expenses")
    category = relationship("PersonalCategory", back_populates="expenses")