from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models as app_models
from app.security import require_tab
from .. import schemas, invoices_crud

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

can_access_invoices = require_tab("invoices")

# ⚠️ ترتيب حاسم: كل مسار حرفي بجزء واحد (مثل /returns/, /sold-faulty-chassis/)
# يجب أن يُسجَّل قبل `/{invoice_id}/` بجزء واحد، وإلا سيُفسَّر النص الحرفي
# كمعرّف فاتورة ويفشل بخطأ 422 قبل الوصول للمسار الصحيح إطلاقًا.


@router.post("/", response_model=schemas.InvoiceResponse)
def create_invoice(
    data: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.create_invoice(db, data, current_user.id)


@router.get("/", response_model=schemas.PaginatedInvoices)
def get_invoices(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None, description="بحث برقم الفاتورة"),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    items, total = invoices_crud.get_invoices(
        db, skip=skip, limit=limit,
        customer_name=customer_name, status=status, search=search
    )
    return {"items": items, "total": total}


@router.get("/stats/summary/", response_model=schemas.InvoiceStatsResponse)
def get_invoice_stats(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_invoice_stats(db)


@router.get("/available-chassis/", response_model=list[schemas.AvailableChassisResponse])
def get_available_chassis(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_available_chassis_with_price(db)


@router.get("/pending-refunds/", response_model=list[schemas.PendingInvoiceRefundResponse])
def get_pending_refunds(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_pending_invoice_refunds(db)


@router.get("/resolved-refunds/", response_model=list[schemas.ResolvedInvoiceRefundResponse])
def get_resolved_refunds(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_resolved_invoice_refunds(db)


@router.get("/returns/returnable-chassis/", response_model=list[schemas.ReturnableChassisResponse])
def get_returnable_chassis(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_returnable_chassis(db)


@router.get("/returns/", response_model=schemas.PaginatedReturns)
def get_returns(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    items, total = invoices_crud.get_returns(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


@router.post("/returns/", response_model=schemas.ChassisReturnResponse)
def create_return(
    data: schemas.ChassisReturnCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.create_return(db, data, current_user.id)


@router.get("/sold-faulty-chassis/", response_model=list[schemas.SoldFaultyChassisResponse])
def get_sold_faulty_chassis(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_sold_faulty_chassis(db)


@router.get("/{invoice_id}/", response_model=schemas.InvoiceResponse)
def get_invoice_detail(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    invoice = invoices_crud.get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")
    return invoice


@router.post("/{invoice_id}/payments/", response_model=schemas.InvoiceResponse)
def add_payment(
    invoice_id: int,
    data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.add_payment(db, invoice_id, data, current_user.id)


@router.put("/{invoice_id}/payments/{payment_id}/", response_model=schemas.InvoiceResponse)
def update_payment(
    invoice_id: int,
    payment_id: int,
    data: schemas.PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.update_payment(db, invoice_id, payment_id, data, current_user.id)


# 🆕 حذف دفعة بالكامل (تصحيح خطأ إدخال) — راجع invoices_crud.delete_payment
# للتفاصيل، خصوصًا لماذا لا يُشكّل هذا خطرًا على فواتير مكتملة الدفع
@router.delete("/{invoice_id}/payments/{payment_id}/", response_model=schemas.InvoiceResponse)
def delete_payment(
    invoice_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.delete_payment(db, invoice_id, payment_id, current_user.id)


@router.put("/{invoice_id}/items/{item_id}/", response_model=schemas.InvoiceResponse)
def update_invoice_item(
    invoice_id: int,
    item_id: int,
    data: schemas.InvoiceItemUpdate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.update_invoice_item(db, invoice_id, item_id, data, current_user.id)


# 🆕 حذف بند فاتورة عادي (خطأ إدخال، وليس إرجاع). النتيجة تختلف حسب الحالة:
# - إن كانت الفاتورة بلا أي مدفوعات وهذا آخر بند: تُحذف الفاتورة بالكامل
#   فعليًا (لا تُرجع InvoiceResponse، بل {"deleted": true}).
# - إن وُجدت مدفوعات وهذا آخر بند: يتطلب `confirm=true` (409 أول مرة).
@router.delete("/{invoice_id}/items/{item_id}/")
def delete_invoice_item(
    invoice_id: int,
    item_id: int,
    confirm: bool = Query(default=False, description="تأكيد إلغاء الفاتورة كاملة إن كان هذا آخر بند فيها وبها مدفوعات"),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    result = invoices_crud.delete_invoice_item(db, invoice_id, item_id, current_user.id, confirm_delete_invoice=confirm)
    if result is None:
        return {"deleted": True, "message": "تم حذف الفاتورة بالكامل بنجاح"}
    return schemas.InvoiceResponse.model_validate(result)


@router.post("/{invoice_id}/cancel/", response_model=schemas.InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    data: schemas.InvoiceCancel,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.cancel_invoice(db, invoice_id, data, current_user.id)


@router.post("/{invoice_id}/refund/mark-refunded/", response_model=schemas.RefundActionResult)
def mark_invoice_refunded(
    invoice_id: int,
    data: schemas.InvoiceRefundMark,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.mark_invoice_refunded(db, invoice_id, data.amount, current_user.id)


@router.post("/{invoice_id}/refund/reallocate/", response_model=schemas.RefundActionResult)
def reallocate_invoice_refund(
    invoice_id: int,
    data: schemas.InvoiceRefundReallocate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.reallocate_invoice_refund(db, invoice_id, data, current_user.id)


@router.get("/customers/{customer_id}/statement/", response_model=schemas.CustomerStatementResponse)
def get_customer_statement(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_customer_statement(db, customer_id)