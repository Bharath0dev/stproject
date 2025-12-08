# schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Union, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    phone: str
    is_invited: bool

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserData(BaseModel):
    id: UUID


# --- category schemas ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(income|expense)$")

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Expense schemas
class ExpenseCreate(BaseModel):
    category_id: Optional[int] = None
    amount: Decimal
    description: Optional[str] = None
    date: date

class ExpenseUpdate(BaseModel):
    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    # Change back to Optional, but set the default explicitly to None
    date: Optional[date] = None

class ExpenseRead(BaseModel):
    id: int
    user_id: UUID
    category_id: Optional[int]
    amount: Decimal
    description: Optional[str]
    date: date
    created_at: datetime

    class Config:
        from_attributes = True

class CreateGroup(BaseModel):
    name: str

class GroupRead(BaseModel):
    id: int
    name: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AddMembersToGroups(BaseModel):
    phone: str

class AddMembersToGroupsRead(BaseModel):
    id: int
    group_id: int
    user_id: UUID
    joined_at: datetime
    is_admin: bool
    
    model_config = ConfigDict(from_attributes=True)


class ExpenseSplitIn(BaseModel):
    user_id: UUID
    # For exact/percentage split: share amount or percentage or pre-calculated share
    share: Decimal  # interpret based on split_type

class GroupExpenseBase(BaseModel):
    total_amount: Decimal
    description: Optional[str] = None
    date: date
    splits: List[ExpenseSplitIn]

class GroupExpenseRead(GroupExpenseBase):
    id: int
    added_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


