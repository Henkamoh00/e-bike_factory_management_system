from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, workshop_crud, reports_crud
from ..security import get_current_user, require_tab

router = APIRouter(prefix="/api", tags=["bike-options"])

can_manage_settings = require_tab("settings")
can_view_archive = require_tab("archive")


# ====================== BIKE TYPES ======================
@router.get("/bike-types/simple/")
def search_bike_types(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """🆕 بحث خفيف للقوائم المنسدلة"""
    types = workshop_crud.search_bike_types_simple(db, q=q, limit=limit)
    return [{"id": t.id, "name": t.name} for t in types]


@router.get("/bike-types/", response_model=schemas.PaginatedBikeTypes)
def get_bike_types(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    items, total = reports_crud.get_bike_types_with_usage(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


# 🛡️📝 ملاحظة توثيقية مقصودة (وليست ثغرة أمنية):
# صلاحية الإنشاء هنا هي get_current_user فقط (أي مستخدم مسجّل دخول بغض
# النظر عن صلاحية تبويب "settings")، وليست can_manage_settings كما قد
# يُتوقع بالمقارنة مع PUT/DELETE أدناه. هذا **مقصود عمدًا** ويطابق تمامًا
# نفس النمط المتّبع في create_worker داخل workers.py، للسبب التالي:
#   AssemblyFormModal.vue يسمح لأي عامل يملك صلاحية تبويب "assembly" فقط
#   (وليس "settings") بإضافة نوع دراجة جديد أثناء تسجيل عملية تجميع
#   (زر "+ إضافة نوع جديد" داخل المودال) دون أن يحتاج لصلاحية إعدادات كاملة.
# أما التعديل (PUT) والحذف (DELETE) فتبقى محصورة بـ can_manage_settings
# عمدًا لأنها عمليات أكثر حساسية تُغيّر أو تُخفي بيانات موجودة مسبقًا،
# بخلاف مجرد إضافة قيمة جديدة للقائمة.
# ⚠️ لا تُغيّر هذا إلى can_manage_settings دون التأكد من تحديث الفرونت إند
# (AssemblyFormModal.vue) ليتعامل مع احتمال ظهور خطأ 403 لغير الأدمن/المشرف.
@router.post("/bike-types/")
def create_bike_type(data: schemas.BikeTypeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.BikeType).filter(
        models.BikeType.name == data.name,
        models.BikeType.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="نوع الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_type(db, data.name, current_user.id)


@router.put("/bike-types/{type_id}/")
def update_bike_type(type_id: int, data: schemas.BikeTypeUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    try:
        return workshop_crud.update_bike_type(db, type_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-types/{type_id}/")
def delete_bike_type(type_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    try:
        workshop_crud.soft_delete_bike_type(db, type_id, current_user.id)
        return {"message": "تم حذف نوع الدراجة بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-types/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_types(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    return reports_crud.bulk_soft_delete_bike_types(db, payload.ids, current_user.id)


# ====================== BIKE COLORS ======================
@router.get("/bike-colors/simple/")
def search_bike_colors(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """🆕 بحث خفيف للقوائم المنسدلة"""
    colors = workshop_crud.search_bike_colors_simple(db, q=q, limit=limit)
    return [{"id": c.id, "name": c.name} for c in colors]


@router.get("/bike-colors/", response_model=schemas.PaginatedBikeColors)
def get_bike_colors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    items, total = reports_crud.get_bike_colors_with_usage(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


# 🛡️📝 نفس الملاحظة أعلاه بخصوص create_bike_type تنطبق هنا حرفيًا:
# get_current_user مقصودة عمدًا لتمكين "+ إضافة لون جديد" داخل
# AssemblyFormModal.vue من قِبل أي عامل بصلاحية تبويب "assembly"، بينما
# PUT/DELETE تبقى محصورة بـ can_manage_settings.
@router.post("/bike-colors/")
def create_bike_color(data: schemas.BikeColorCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.BikeColor).filter(
        models.BikeColor.name == data.name,
        models.BikeColor.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="لون الدراجة موجود مسبقاً")
    return workshop_crud.get_or_create_bike_color(db, data.name, current_user.id)


@router.put("/bike-colors/{color_id}/")
def update_bike_color(color_id: int, data: schemas.BikeColorUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    try:
        return workshop_crud.update_bike_color(db, color_id, data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/bike-colors/{color_id}/")
def delete_bike_color(color_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    try:
        workshop_crud.soft_delete_bike_color(db, color_id, current_user.id)
        return {"message": "تم حذف اللون بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bike-colors/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_bike_colors(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_settings)):
    return reports_crud.bulk_soft_delete_bike_colors(db, payload.ids, current_user.id)


@router.get("/bike-types/archived/", response_model=schemas.PaginatedArchivedBikeOptions)
def get_archived_bike_types(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_archive)
):
    items, total = workshop_crud.get_archived_bike_types(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/bike-types/{type_id}/restore/")
def restore_bike_type(type_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.restore_bike_type(db, type_id, current_user.id)
        return {"message": "تم استعادة النوع بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bike-colors/archived/", response_model=schemas.PaginatedArchivedBikeOptions)
def get_archived_bike_colors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_archive)
):
    items, total = workshop_crud.get_archived_bike_colors(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/bike-colors/{color_id}/restore/")
def restore_bike_color(color_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        workshop_crud.restore_bike_color(db, color_id, current_user.id)
        return {"message": "تم استعادة اللون بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))