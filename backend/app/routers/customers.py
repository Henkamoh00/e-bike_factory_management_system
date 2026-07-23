from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, models

router = APIRouter(prefix="/api/customers", tags=["customers"])

@router.get("/")
def get_customers(db: Session = Depends(get_db)):
    return crud.get_customers_with_sales(db)


@router.post("/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.name == customer.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return crud.create_customer(db, customer)


@router.put("/{customer_id}/")
def update_customer(customer_id: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    try:
        return crud.update_customer(db, customer_id, customer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{customer_id}/")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    try:
        crud.soft_delete_customer(db, customer_id)
        return {"message": "تم حذف العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_customers(payload: schemas.BulkIds, db: Session = Depends(get_db)):
    return crud.bulk_soft_delete_customers(db, payload.ids)