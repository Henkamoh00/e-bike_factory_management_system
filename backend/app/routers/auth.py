from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ..database import get_db
from .. import schemas, models, auth_crud
from ..security import (
    create_access_token, get_current_user,
    set_auth_cookies, clear_auth_cookies, REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_COOKIE_NAME,
)
from ..rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login/", response_model=schemas.UserResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth_crud.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")

    user.last_login = func.now()
    db.commit()
    db.refresh(user)
    user.role = user.role_obj.name
    user.role_label = user.role_obj.label

    access_token = create_access_token({"sub": user.username, "role": user.role})
    raw_refresh_token = auth_crud.create_refresh_token(
        db, user.id,
        days_valid=REFRESH_TOKEN_EXPIRE_DAYS,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # 🛡️ التوكنات توضع في httpOnly cookies فقط، ولا تُعاد في جسم الاستجابة إطلاقاً
    set_auth_cookies(response, access_token, raw_refresh_token)

    return user


@router.post("/refresh/", response_model=schemas.UserResponse)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    🆕 نقطة نهاية جديدة: يستخدمها الفرونت إند تلقائيًا عند انتهاء صلاحية
    access_token (15 دقيقة) للحصول على واحد جديد دون إعادة تسجيل الدخول،
    طالما refresh_token (7 أيام) ما زال صالحًا وغير مُبطَل.
    """
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise HTTPException(status_code=401, detail="لا توجد جلسة نشطة، يرجى تسجيل الدخول")

    user = auth_crud.verify_and_rotate_refresh_token(db, raw_refresh_token)
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً")

    new_access_token = create_access_token({"sub": user.username, "role": user.role})
    new_raw_refresh_token = auth_crud.create_refresh_token(
        db, user.id,
        days_valid=REFRESH_TOKEN_EXPIRE_DAYS,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    set_auth_cookies(response, new_access_token, new_raw_refresh_token)
    return user


@router.post("/logout/")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """🆕 يُبطل refresh token في قاعدة البيانات ويمسح الكوكيز من المتصفح"""
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token:
        auth_crud.revoke_refresh_token(db, raw_refresh_token)
    clear_auth_cookies(response)
    return {"message": "تم تسجيل الخروج بنجاح", "status": "success"}


@router.get("/me", response_model=schemas.UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user