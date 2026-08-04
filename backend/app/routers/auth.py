from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ..database import get_db
from .. import schemas, models, auth_crud
from ..security import create_access_token, get_current_user
from ..rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


# 🛡️ الحد الأهم في كامل النظام: يمنع هجمات Brute Force على كلمات المرور.
# 5 محاولات لكل IP كل دقيقة — كافية لمستخدم حقيقي أخطأ بكتابة كلمة المرور،
# وصارمة بما يكفي لإبطاء أي محاولة تخمين آلية.
@router.post("/login/", response_model=schemas.Token)
@limiter.limit("5/minute")
def login(request: Request, payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth_crud.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")

    user.last_login = func.now()
    db.commit()
    db.refresh(user)
    user.role = user.role_obj.name
    user.role_label = user.role_obj.label

    token = create_access_token({"sub": user.username, "role": user.role})

    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user