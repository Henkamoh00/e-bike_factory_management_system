from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from . import models, schemas
from .security import hash_password, verify_password


def create_user(db: Session, data: schemas.UserCreate):
    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing:
        raise ValueError("اسم المستخدم موجود مسبقاً")

    user = models.User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.is_deleted == False
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_users(db: Session):
    return db.query(models.User)\
              .filter(models.User.is_deleted == False)\
              .order_by(models.User.id.desc()).all()


def update_user(db: Session, user_id: int, data: schemas.UserUpdate):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError("المستخدم غير موجود")
    user.is_deleted = True
    user.is_active = False
    db.commit()
    return user