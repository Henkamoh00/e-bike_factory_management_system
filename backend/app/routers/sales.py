from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import crud, schemas

router = APIRouter(prefix="/api/sales", tags=["sales"])

@router.post("/", response_model=schemas.SaleResponse)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_sale(db, sale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.SaleResponse])
def get_all_sales(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """عرض كل المبيعات (نشطة وملغاة)"""
    return crud.get_sales(db, skip=skip, limit=limit)


@router.post("/{sale_id}/cancel/", response_model=schemas.SaleResponse)
def cancel_sale(sale_id: int, payload: schemas.SaleCancel, db: Session = Depends(get_db)):
    """إلغاء عملية بيع (لا يحذف السجل، فقط يعلّمه كملغى مع الاحتفاظ بالسبب)"""
    try:
        return crud.cancel_sale(db, sale_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))