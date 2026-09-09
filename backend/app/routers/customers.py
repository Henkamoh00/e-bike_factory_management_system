from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from ..database import get_db
from .. import customers_crud, schemas, models
from ..security import require_tab, require_any_tab
from ..rate_limit import limiter, get_rate_limit_key

router = APIRouter(prefix="/api/customers", tags=["customers"])

# 🛡️🆕 إصلاح: مستخدم يملك تبويب "invoices" فقط (بلا "customers") كان
# محجوبًا بالكامل عن أي endpoint هنا، رغم أن تدفق الفوترة يحتاج بالضرورة
# إلى: البحث السريع عن عميل (اختياره في الفاتورة)، القائمة الكاملة (تبويب
# "كشف حساب عميل")، وإضافة عميل جديد من داخل فورم الفاتورة مباشرة.
# نفصل الصلاحيات: "عرض/إضافة" مفتوحة لمن يملك customers أو invoices،
# بينما "التعديل/الحذف/الأرشفة" (إدارة عملاء حقيقية) تبقى حكرًا على customers فقط.
can_view_customers = require_any_tab("customers", "invoices")
can_manage_customers = require_tab("customers")
can_view_archive = require_tab("archive")


@router.get("/simple/")
def search_customers(
    q: str | None = Query(default=None, description="بحث باسم العميل"),
    limit: int = Query(default=20, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_customers)
):
    """🆕 بحث خفيف للقوائم المنسدلة (SaleModal مثلاً)"""
    customers = customers_crud.search_customers_simple(db, q=q, limit=limit)
    return [{"id": c.id, "name": c.name} for c in customers]


@router.get("/", response_model=schemas.PaginatedCustomers)
def get_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_customers)
):
    items, total = customers_crud.get_customers_with_sales(db, skip=skip, limit=limit, search=search)
    return {"items": items, "total": total}


# 🛡️🆕 إضافة عميل تبقى متاحة لمن يملك invoices أيضًا (وليس فقط customers)
# لأن "+ إضافة عميل جديد" داخل فورم الفاتورة يعتمد على هذا المسار مباشرة
@router.post("/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_customers)):
    existing = db.query(models.Customer).filter(
        models.Customer.name == customer.name,
        models.Customer.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return customers_crud.create_customer(db, customer, current_user.id)


@router.put("/{customer_id}/")
def update_customer(customer_id: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_customers)):
    try:
        return customers_crud.update_customer(db, customer_id, customer, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{customer_id}/")
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_manage_customers)):
    try:
        customers_crud.soft_delete_customer(db, customer_id, current_user.id)
        return {"message": "تم حذف العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 🛡️🆕 حد على bulk-delete — الآن لكل مستخدم
@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour", key_func=get_rate_limit_key)
def bulk_delete_customers(
    request: Request,
    payload: schemas.BulkIds,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_manage_customers)
):
    return customers_crud.bulk_soft_delete_customers(db, payload.ids, current_user.id)


@router.get("/archived/", response_model=schemas.PaginatedArchivedCustomers)
def get_archived_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_view_archive)
):
    items, total = customers_crud.get_archived_customers(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/{customer_id}/restore/")
def restore_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        customers_crud.restore_customer(db, customer_id, current_user.id)
        return {"message": "تم استعادة العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))