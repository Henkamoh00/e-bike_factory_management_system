import os
import secrets
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models, schemas

# 🛡️ إجبار تعيين JWT_SECRET_KEY من متغيرات البيئة — لا قيمة افتراضية إطلاقًا.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "❌ متغير البيئة JWT_SECRET_KEY غير مُعرَّف. "
        "يجب تعيين قيمة عشوائية قوية وسرية لهذا المتغير قبل تشغيل السيرفر "
        "(مثال للتوليد: python -c \"import secrets; print(secrets.token_hex(32))\"). "
        "تم إيقاف التشغيل عمدًا لمنع استخدام مفتاح افتراضي غير آمن في الإنتاج."
    )

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

ACCESS_COOKIE_NAME = "ebike_access"
REFRESH_COOKIE_NAME = "ebike_refresh"

# 🛡️🆕 حماية CSRF — نمط Double Submit Cookie:
# - CSRF cookie غير httpOnly (يجب أن يقرأها JS ليرسلها بالهيدر يدويًا)
# - أي طلب مُغيِّر للحالة (POST/PUT/DELETE/PATCH) من عميل يحمل جلسة كوكيز
#   يجب أن يُرفق هيدر X-CSRF-Token مطابقًا تمامًا لقيمة الكوكي
# - موقع خبيث (cross-site) لا يستطيع قراءة كوكيز الضحية بسبب Same-Origin Policy
#   حتى لو استطاع إرسال الكوكيز تلقائيًا ضمن الطلب (بسبب SameSite=None)،
#   لذا لا يستطيع بناء الهيدر الصحيح إطلاقًا — هذا هو جوهر الحماية.
CSRF_COOKIE_NAME = "ebike_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

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
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _cookie_kwargs(max_age_seconds: int, http_only: bool = True) -> dict:
    return {
        "httponly": http_only,
        "secure": COOKIE_SECURE,
        "samesite": "none" if COOKIE_SECURE else "lax",
        "domain": COOKIE_DOMAIN,
        "path": "/",
        "max_age": max_age_seconds,
    }


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str):
    """🛡️🆕 يضبط كوكي CSRF غير httpOnly — يجب أن يبقى قابلاً للقراءة من JS"""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        **_cookie_kwargs(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, http_only=False),
    )


def clear_csrf_cookie(response: Response):
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        domain=COOKIE_DOMAIN,
        path="/",
        samesite="none" if COOKIE_SECURE else "lax",
        secure=COOKIE_SECURE,
    )


def set_auth_cookies(response: Response, access_token: str, raw_refresh_token: str):
    """يضبط كوكيز الـ access و refresh و CSRF معًا على الاستجابة"""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        **_cookie_kwargs(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        **_cookie_kwargs(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
    )
    # 🛡️🆕 كوكي CSRF جديد يُصدَر مع كل جلسة (login أو refresh) لمنع إعادة استخدام
    # توكن CSRF قديم عبر جلسات مختلفة
    set_csrf_cookie(response, generate_csrf_token())


def clear_auth_cookies(response: Response):
    """يمسح كوكيز الجلسة بالكامل (تسجيل الخروج)"""
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        response.delete_cookie(
            key=name,
            domain=COOKIE_DOMAIN,
            path="/",
            samesite="none" if COOKIE_SECURE else "lax",
            secure=COOKIE_SECURE,
        )
    clear_csrf_cookie(response)


def _extract_access_token(request: Request, header_token: str | None) -> str | None:
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    return header_token


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صالحة أو منتهية",
    )
    actual_token = _extract_access_token(request, token)
    if not actual_token:
        raise credentials_exception
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None or payload.get("type") != "access":
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
    if user.role == models.RoleNames.ADMIN:
        user.allowed_tabs = list(schemas.ALL_TAB_IDS)
    else:
        user.allowed_tabs = user.role_obj.allowed_tabs or []

    return user


def require_roles(*allowed_role_names: str):
    def checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية للقيام بهذا الإجراء",
            )
        return current_user
    return checker


def require_tab(tab_id: str):
    def checker(current_user: models.User = Depends(get_current_user)):
        if tab_id not in (current_user.allowed_tabs or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية الوصول لهذا التبويب",
            )
        return current_user
    return checker


def require_any_tab(*tab_ids: str):
    def checker(current_user: models.User = Depends(get_current_user)):
        allowed = current_user.allowed_tabs or []
        if not any(t in allowed for t in tab_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية الوصول لهذا المورد",
            )
        return current_user
    return checker