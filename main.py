from fastapi import FastAPI
from database import engine, Base
import models   # ensure your models file imported so tables are registered
import schemas
import bcrypt
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal


app = FastAPI()

Base.metadata.create_all(bind=engine)

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

@app.post("/register/", response_model=schemas.UserOut)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # create the user

    plain_pw = user_in.password
    hashed_pw = hash_password(plain_pw)

    user = models.User(
        email = user_in.email,
        password_hash = hashed_pw,
        full_name = user_in.full_name
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

    return {"message": "Login successful", "user_id": str(user.id)}