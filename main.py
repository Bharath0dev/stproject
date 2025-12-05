from fastapi import FastAPI, status, Request
from database import engine, Base
import models   # ensure your models file imported so tables are registered
import schemas
import bcrypt
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt
from typing import List, Optional
from datetime import datetime, timedelta, date
from typing import Dict
from uuid import UUID

app = FastAPI()

Base.metadata.create_all(bind=engine)

# JWT Configuration
SECRET_KEY = "your-secret-key"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/hi")
def sayhi():
    return {"message": "Hi"}

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    # hashed is bytes, convert to str
    return hashed.decode("utf-8")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/register/", response_model=schemas.UserOut)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # check if email already exists
    # existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    existing_user = db.query(models.User).filter(models.User.phone == user_in.phone).first()
    
    if existing_user:
        is_invited = db.query(models.User).filter(models.User.phone == user_in.phone, models.User.is_invited == True).first()
        if is_invited:
            existing_user.email = user_in.email
            existing_user.full_name = user_in.full_name
            existing_user.password_hash = hash_password(user_in.password)
            existing_user.is_invited = False

            db.commit()
            db.refresh(existing_user)
            return existing_user
        else:
            raise HTTPException(status_code=400, detail="User already registered")
        
    # create the user

    plain_pw = user_in.password
    hashed_pw = hash_password(plain_pw)

    user = models.User(
        email = user_in.email,
        password_hash = hashed_pw,
        full_name = user_in.full_name,
        phone = user_in.phone
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login/")
def user_login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not registered")

    # user.password_hash is the hashed password stored
    hashed_pw = user.password_hash.encode("utf-8")
    plain_pw = user_in.password.encode("utf-8")

    # Use bcrypt.checkpw to verify
    if not bcrypt.checkpw(plain_pw, hashed_pw):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "message": "Login successful",
        "user_id": str(user.id),
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/userdata/{user_id}", response_model=schemas.UserOut)
def user_data(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user

# --- Category endpoints ---
@app.post("/categories/", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    cat: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    new = models.PersonalCategory(name=cat.name, type=cat.type, user_id=user.id)
    db.add(new)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Category with same name & type already exists")
    db.refresh(new)
    return new


@app.get("/categories/", response_model=List[schemas.CategoryRead])
def get_categories(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    cats = db.query(models.PersonalCategory).filter(models.PersonalCategory.user_id == user.id).all()
    return cats



# --- Expense endpoints ---
@app.post("/expenses/", response_model=schemas.ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Verify category belongs to user if category_id is provided
    if expense.category_id:
        category = db.query(models.PersonalCategory).filter(
            models.PersonalCategory.id == expense.category_id,
            models.PersonalCategory.user_id == user.id
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found or doesn't belong to you")
    
    new_expense = models.PersonalExpense(
        user_id=user.id,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description,
        date=expense.date
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense



@app.get("/expenses/", response_model=List[schemas.ExpenseRead])
def get_expenses(
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    query = db.query(models.PersonalExpense).filter(models.PersonalExpense.user_id == user.id)
    
    # Apply filters if provided
    if category_id:
        query = query.filter(models.PersonalExpense.category_id == category_id)
    if start_date:
        query = query.filter(models.PersonalExpense.date >= start_date)
    if end_date:
        query = query.filter(models.PersonalExpense.date <= end_date)
    
    expenses = query.order_by(models.PersonalExpense.date.desc()).all()
    return expenses


@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseRead)
# CHANGE: Inject the Request object directly
async def update_expense( # <-- Must be an async function to use request.json()
    expense_id: int,
    request: Request, # <-- Inject the raw request object
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Retrieve the raw dictionary data asynchronously
    try:
        # Await the json() method of the Request object
        update_data = await request.json() 
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    expense = db.query(models.PersonalExpense).filter(
        models.PersonalExpense.id == expense_id,
        models.PersonalExpense.user_id == user.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # --- MANUAL DATE & VALIDATION FIX (Keep this logic) ---
    
    # 1. Manual Date Parsing
    if "date" in update_data and update_data["date"] is not None:
        if not isinstance(update_data["date"], str):
             raise HTTPException(status_code=400, detail="Date must be a string in YYYY-MM-DD format.")
        
        try:
            date_str = update_data["date"]
            # datetime.strptime returns a datetime object, use .date()
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date() 
            update_data["date"] = parsed_date
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # 2. Manual Amount Validation (Ensures Decimal conversion)
    if "amount" in update_data and update_data["amount"] is not None:
        try:
            update_data["amount"] = Decimal(str(update_data["amount"]))
        except Exception:
            raise HTTPException(status_code=400, detail="Amount must be a valid number.")

    # 3. Category Validation (Keep existing logic)
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.query(models.PersonalCategory).filter(
            models.PersonalCategory.id == update_data["category_id"],
            models.PersonalCategory.user_id == user.id
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found or doesn't belong to you")
            
    # Update the expense with provided fields
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense



@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    expense = db.query(models.PersonalExpense).filter(
        models.PersonalExpense.id == expense_id,
        models.PersonalExpense.user_id == user.id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return None

@app.post("/groups/", response_model=schemas.GroupRead)
def create_group(
    group_in: schemas.CreateGroup, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)  # Get from token
):
    group = models.Groups(
        name=group_in.name,
        created_by=user.id  # Use authenticated user's ID
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    # Automatically add creator as admin member
    creator_member = models.GroupMembers(
        group_id=group.id,
        user_id=user.id,
        is_admin=True
    )
    db.add(creator_member)
    db.commit()
    
    return group


@app.get("/groups/", response_model=List[schemas.GroupRead])
def get_my_groups(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Get groups where user is a member
    member_records = db.query(models.GroupMembers).filter(
        models.GroupMembers.user_id == user.id
    ).all()
    
    group_ids = [m.group_id for m in member_records]
    groups = db.query(models.Groups).filter(models.Groups.id.in_(group_ids)).all()
    return groups


# @app.post("/groups/{group_id}/members/", response_model=schemas.AddMembersToGroupsRead, status_code=status.HTTP_201_CREATED)
# def add_group_member(
#     group_id: int,  # Changed from str to int
#     member_in: schemas.AddMembersToGroups,
#     db: Session = Depends(get_db),
#     user: models.User = Depends(get_current_user)
# ):
#     # Check if current user is a member of the group (any member can add others)
#     member_check = db.query(models.GroupMembers).filter(
#         models.GroupMembers.group_id == group_id,
#         models.GroupMembers.user_id == user.id
#     ).first()
    
#     if not member_check:
#         raise HTTPException(status_code=403, detail="Only group members can add other members")
    
#     # Check if user to be added exists
#     user_exists = db.query(models.User).filter(models.User.id == member_in.user_id).first()
#     if not user_exists:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     # Check if already a member
#     existing = db.query(models.GroupMembers).filter(
#         models.GroupMembers.group_id == group_id,
#         models.GroupMembers.user_id == member_in.user_id
#     ).first()
    
#     if existing:
#         raise HTTPException(status_code=400, detail="User is already a member")
    
#     # Add member
#     new_member = models.GroupMembers(
#         group_id=group_id,
#         user_id=member_in.user_id,
#         is_admin=member_in.is_admin
#     )
#     db.add(new_member)
#     db.commit()
#     db.refresh(new_member)
#     return new_member


# @app.post("/groups/{group_id}/add_members", response_model=schemas.AddMembersToGroupsRead, status_code=status.HTTP_201_CREATED)
# def add_members_to_group(
#     group_id: UUID,
#     user_mobile_number: schemas.AddMembersToGroups
# ):
#     #check user mobile number in users table
#     #if user exists add user with user id into this group
#     #if user does not exists insert a new row in user table with is_invited true, email and full_name are null
#     #after creation of partial user with is_invited true, add the user to the group
    
#     return "done"

@app.post("/groups/{group_id}/add_members", status_code=status.HTTP_201_CREATED)
def add_members_to_group(
    group_id: int,
    member_data: schemas.AddMembersToGroups,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Check group exists
    group = db.query(models.Groups).filter(models.Groups.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # 2. (Optionally) Check current_user has permission to invite (e.g. is admin)
    member = db.query(models.GroupMembers).filter(
        models.GroupMembers.group_id == group_id,
        models.GroupMembers.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Only group members can invite")

    # 3. Try find user by phone
    user = db.query(models.User).filter(models.User.phone == member_data.phone).first()
    if not user:
        # 4. Create partial user
        user = models.User(
            email=None,
            password_hash=None,
            full_name=None,
            phone=member_data.phone,
            is_invited=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 5. Check if already member
    existing = db.query(models.GroupMembers).filter(
        models.GroupMembers.group_id == group_id,
        models.GroupMembers.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already member")

    # 6. Add membership
    membership = models.GroupMembers(
        group_id=group_id,
        user_id=user.id,
        is_admin=False
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership

