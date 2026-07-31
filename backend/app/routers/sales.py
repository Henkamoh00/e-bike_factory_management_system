from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas, models
from ..security import require_roles

router = APIRouter(prefix="/api/sales", tags=["sales"])

admin_or_supervisor = require_roles(models.RoleNames.ADMIN, models.RoleNames.SUPERVISOR)


@router.post("/", response_model=schemas.SaleResponse)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        db_sale = crud.create_sale(db, sale, current_user.id)
        db_sale.customer_name = db_sale.customer.name if db_sale.customer else "غير معروف"
        db_sale.created_by_username = current_user.username
        db_sale.cancelled_by_username = None
        return db_sale
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.SaleResponse])
def get_all_sales(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    """عرض كل المبيعات (نشطة وملغاة)"""
    return crud.get_sales(db, skip=skip, limit=limit)


@router.post("/{sale_id}/cancel/", response_model=schemas.SaleResponse)
def cancel_sale(sale_id: int, payload: schemas.SaleCancel, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    """إلغاء عملية بيع (لا يحذف السجل، فقط يعلّمه كملغى مع الاحتفاظ بالسبب)"""
    try:
        sale = crud.cancel_sale(db, sale_id, payload, current_user.id)
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"
        sale.created_by_username = sale.created_by.username if sale.created_by else None
        sale.cancelled_by_username = current_user.username
        return sale
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-cancel/", response_model=schemas.BulkActionResult)
def bulk_cancel_sales(payload: schemas.BulkCancel, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        return crud.bulk_cancel_sales(db, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))