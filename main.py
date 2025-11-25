from fastapi import FastAPI
from database import engine, Base
import models   # ensure your models file imported so tables are registered
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
