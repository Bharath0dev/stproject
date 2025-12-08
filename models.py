from uuid import uuid4
from sqlalchemy import Column, String, DateTime, LargeBinary, UniqueConstraint, Integer, ForeignKey, Numeric, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_invited = Column(Boolean, default=False, nullable=False)
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


class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("GroupMembers", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("GroupExpenses", back_populates="group", cascade="all, delete-orphan")



class GroupMembers(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_admin = Column(Boolean, nullable=False)

    group = relationship("Groups", back_populates="members")
    user = relationship("User")


class GroupExpenses(Base):
    __tablename__ = "group_expenses"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)  # Fixed: "group.id" -> "groups.id"
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group = relationship("Groups", back_populates="expenses")
    added_by_user = relationship("User", foreign_keys=[added_by])
    splits = relationship("GroupExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


class GroupExpenseSplit(Base):
    __tablename__ = "group_expense_splits"
    
    id = Column(Integer, primary_key=True, index=True)
    group_expense_id = Column(Integer, ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    share_amount = Column(Numeric(12, 2), nullable=False)  # How much this user owes
    paid_amount = Column(Numeric(12, 2), default=0, nullable=False)  # How much paid so far
    settled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    expense = relationship("GroupExpenses", back_populates="splits")
    user = relationship("User")