from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db
from .. import sales_crud, schemas, models
from ..security import require_tab
from ..rate_limit import limiter

router = APIRouter(prefix="/api/sales", tags=["sales"])

can_access_sales = require_tab("sales")


@router.post("/", response_model=schemas.SaleResponse)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_sales)):
    try:
        db_sale = sales_crud.create_sale(db, sale, current_user.id)
        db_sale.customer_name = db_sale.customer.name if db_sale.customer else "غير معروف"
        db_sale.created_by_username = current_user.username
        db_sale.cancelled_by_username = None
        return db_sale
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=schemas.PaginatedSales)
def get_all_sales(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=schemas.DEFAULT_PAGE_LIMIT, ge=1, le=schemas.MAX_PAGE_LIMIT),
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_sales)
):
    """عرض المبيعات (نشطة وملغاة) مُصفَّحة ومُفلتَرة من السيرفر"""
    items, total = sales_crud.get_sales(
        db, skip=skip, limit=limit,
        customer_name=customer_name, status=status,
        date_from=date_from, date_to=date_to
    )
    return {"items": items, "total": total}


@router.post("/{sale_id}/cancel/", response_model=schemas.SaleResponse)
def cancel_sale(sale_id: int, payload: schemas.SaleCancel, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_sales)):
    try:
        sale = sales_crud.cancel_sale(db, sale_id, payload, current_user.id)
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"
        sale.created_by_username = sale.created_by.username if sale.created_by else None
        sale.cancelled_by_username = current_user.username
        return sale
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🛡️🆕 حد على bulk-cancel (إلغاء عدد كبير من عمليات البيع دفعة واحدة)
@router.post("/bulk-cancel/", response_model=schemas.BulkActionResult)
@limiter.limit("10/hour")
def bulk_cancel_sales(
    request: Request,
    payload: schemas.BulkCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_access_sales)
):
    try:
        return sales_crud.bulk_cancel_sales(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))