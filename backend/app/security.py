import os
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-dev-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 ساعة

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/", auto_error=False)


def hash_password(plain: str) -> str:
    password_bytes = plain.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    password_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صالحة أو منتهية",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(models.User)
        .filter(models.User.username == username, models.User.is_deleted == False)
        .first()
    )
    if user is None or not user.is_active:
        raise credentials_exception

    if user.role_obj is None:
        raise HTTPException(status_code=500, detail="حساب المستخدم بدون دور صالح، راجع الإدارة")

    user.role = user.role_obj.name
    user.role_label = user.role_obj.label
    # 🛡️ admin دائمًا بكل الصلاحيات
    if user.role == models.RoleNames.ADMIN:
        user.allowed_tabs = list(schemas.ALL_TAB_IDS)
    else:
        user.allowed_tabs = user.role_obj.allowed_tabs or []

    return user


def require_roles(*allowed_role_names: str):
    """
    الآن تستقبل أسماء الأدوار كسلاسل نصية بدلاً من قيم Enum:
        dependencies=[Depends(require_roles("admin", "supervisor"))]
    """
    def checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية للقيام بهذا الإجراء",
            )
        return current_user
    return checker


def require_tab(tab_id: str):
    """
    صلاحية ديناميكية: تسمح بالوصول لأي مستخدم يملك هذا التبويب ضمن allowed_tabs
    (بغض النظر عن اسم دوره) — admin يملك كل التبويبات دائمًا تلقائيًا.
    تُستخدم لموارد مثل سجل النشاط والأرشيف التي أصبحت قابلة للتخصيص من "الأدوار".
    """
    def checker(current_user: models.User = Depends(get_current_user)):
        if tab_id not in (current_user.allowed_tabs or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية الوصول لهذا التبويب",
            )
        return current_user
    return checker


def require_any_tab(*tab_ids: str):
    """
    صلاحية ديناميكية مرنة: تسمح بالوصول لأي مستخدم يملك تبويبًا واحدًا على الأقل
    من التبويبات المُمرَّرة — تُستخدم للموارد المشتركة بين عدة تبويبات
    (مثال: بيانات الهياكل تُستخدم من تبويب الورشة، المبيعات، والأعطال معًا).
    """
    def checker(current_user: models.User = Depends(get_current_user)):
        allowed = current_user.allowed_tabs or []
        if not any(t in allowed for t in tab_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية الوصول لهذا المورد",
            )
        return current_user
    return checker