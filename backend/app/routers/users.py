from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, auth_crud, models
from ..security import require_roles, require_tab
from ..rate_limit import limiter, get_rate_limit_key

router = APIRouter(prefix="/api/users", tags=["users"])

can_access_users_tab = require_tab("users")
admin_only = require_roles(models.RoleNames.ADMIN)


def _ensure_not_targeting_admin(db: Session, current_user: models.User, target_id: int):
    """أي دور غير admin لا يمكنه المساس بحساب admin (حذف/تعطيل/تعديل)"""
    if current_user.role == models.RoleNames.ADMIN:
        return
    target = db.query(models.User).filter(models.User.id == target_id).first()
    if target and target.role_obj and target.role_obj.name == models.RoleNames.ADMIN:
        raise HTTPException(status_code=403, detail="لا يمكن التأثير على حساب مدير إلا من قِبل مدير آخر")


@router.get("/", response_model=schemas.PaginatedUsers)
def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    search: str | None = Query(default=None, description="بحث باسم المستخدم"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    items, total = auth_crud.get_users(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


# 🛡️ حد على إنشاء المستخدمين — الآن لكل مستخدم بدل IP
@router.post("/", response_model=schemas.UserResponse)
@limiter.limit("10/minute", key_func=get_rate_limit_key)
def create_user(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    if user.role == models.RoleNames.ADMIN and current_user.role != models.RoleNames.ADMIN:
        raise HTTPException(status_code=403, detail="لا يمكن منح صلاحية مدير إلا من قِبل مدير")
    try:
        return auth_crud.create_user(db, user, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}/", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    if current_user.id == user_id and data.is_active is False:
        raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك الخاص")
    _ensure_not_targeting_admin(db, current_user, user_id)
    if data.role == models.RoleNames.ADMIN and current_user.role != models.RoleNames.ADMIN:
        raise HTTPException(status_code=403, detail="لا يمكن منح صلاحية مدير إلا من قِبل مدير")
    try:
        return auth_crud.update_user(db, user_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}/")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الخاص")
    _ensure_not_targeting_admin(db, current_user, user_id)
    try:
        auth_crud.soft_delete_user(db, user_id, current_user.id)
        return {"message": "تم إلغاء تفعيل المستخدم بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 🛡️🆕 حد صارم على bulk-deactivate — الآن لكل مستخدم
@router.post("/bulk-deactivate/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour", key_func=get_rate_limit_key)
def bulk_deactivate_users(
    request: Request,
    payload: schemas.BulkIds,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    ids = payload.ids
    if current_user.role != models.RoleNames.ADMIN:
        admin_ids = {
            u.id for u in db.query(models.User)
            .join(models.Role)
            .filter(models.User.id.in_(ids), models.Role.name == models.RoleNames.ADMIN)
            .all()
        }
        ids = [i for i in ids if i not in admin_ids]
    return auth_crud.bulk_deactivate_users(db, ids, current_user.id)


@router.post("/bulk-activate/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour", key_func=get_rate_limit_key)
def bulk_activate_users(
    request: Request,
    payload: schemas.BulkIds,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    return auth_crud.bulk_activate_users(db, payload.ids, current_user.id)


# 🛡️🆕 bulk-delete هو الأخطر بين الثلاثة — الآن لكل مستخدم
@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
@limiter.limit("5/hour", key_func=get_rate_limit_key)
def bulk_delete_users(
    request: Request,
    payload: schemas.BulkIds,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_users_tab)
):
    ids = payload.ids
    if current_user.role != models.RoleNames.ADMIN:
        admin_ids = {
            u.id for u in db.query(models.User)
            .join(models.Role)
            .filter(models.User.id.in_(ids), models.Role.name == models.RoleNames.ADMIN)
            .all()
        }
        ids = [i for i in ids if i not in admin_ids]
    return auth_crud.bulk_soft_delete_users(db, ids, current_user.id)


@router.get("/archived/", response_model=schemas.PaginatedArchivedUsers)
def get_archived_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    items, total = auth_crud.get_archived_users(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/{user_id}/restore/")
def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(admin_only)
):
    try:
        auth_crud.restore_user(db, user_id, current_user.id)
        return {"message": "تم استعادة المستخدم بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))