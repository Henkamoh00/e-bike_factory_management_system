from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app import models as app_models
from app.security import require_tab
from .. import schemas, invoices_crud
from ..pdf_generator import generate_invoice_pdf

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

can_access_invoices = require_tab("invoices")

# ⚠️ ترتيب حاسم: كل مسار حرفي بجزء واحد يجب أن يُسجَّل قبل `/{invoice_id}/`


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


@router.get("/credit-refunds/", response_model=schemas.PaginatedCreditRefunds)
def get_credit_refunds(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    items, total = invoices_crud.get_credit_refund_log(db, skip=skip, limit=limit)
    return {"items": items, "total": total}


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


# ====================== رصيد العميل ======================
@router.get("/customers-with-credit/", response_model=list[schemas.CustomerCreditSummary])
def get_customers_with_credit(
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_customers_with_credit(db)


@router.get("/customers/{customer_id}/credit/", response_model=schemas.CustomerCreditBalanceResponse)
def get_customer_credit_balance(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    customer = db.query(app_models.Customer).filter(app_models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    balance = customer.credit_balance if customer.credit_balance is not None else Decimal("0.00")
    return {"customer_id": customer.id, "credit_balance": balance}


@router.get("/customers/{customer_id}/credit/ledger/", response_model=list[schemas.CreditActionResponse])
def get_customer_credit_ledger(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_customer_credit_ledger(db, customer_id)


@router.post("/customers/{customer_id}/credit/deposit/", response_model=schemas.CustomerCreditBalanceResponse)
def deposit_customer_credit(
    customer_id: int,
    data: schemas.CreditDeposit,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.deposit_customer_credit(db, customer_id, data, current_user.id)


@router.post("/customers/{customer_id}/credit/adjust/", response_model=schemas.CustomerCreditBalanceResponse)
def adjust_customer_credit(
    customer_id: int,
    data: schemas.CreditAdjust,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.adjust_customer_credit(db, customer_id, data, current_user.id)


@router.post("/customers/{customer_id}/credit/refund/", response_model=schemas.CustomerCreditBalanceResponse)
def credit_mark_refunded(
    customer_id: int,
    data: schemas.CreditRefundMark,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.credit_mark_refunded(db, customer_id, data.amount, current_user.id)


@router.post("/customers/{customer_id}/credit/reallocate/", response_model=schemas.CreditReallocateResponse)
def credit_reallocate(
    customer_id: int,
    data: schemas.CreditReallocate,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.credit_reallocate(db, customer_id, data, current_user.id)


@router.get("/{invoice_id}/pdf/")
def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    invoice = invoices_crud.get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="الفاتورة غير موجودة")

    try:
        pdf_bytes = generate_invoice_pdf(invoice)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.get("/customers/{customer_id}/statement/", response_model=schemas.CustomerStatementResponse)
def get_customer_statement(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: app_models.User = Depends(can_access_invoices)
):
    return invoices_crud.get_customer_statement(db, customer_id)
