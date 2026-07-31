from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, models
from ..security import require_roles

router = APIRouter(prefix="/api/customers", tags=["customers"])

admin_or_supervisor = require_roles(models.RoleNames.ADMIN, models.RoleNames.SUPERVISOR)


@router.get("/")
def get_customers(db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    return crud.get_customers_with_sales(db)


@router.post("/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    existing = db.query(models.Customer).filter(models.Customer.name == customer.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return crud.create_customer(db, customer, current_user.id)


@router.put("/{customer_id}/")
def update_customer(customer_id: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        return crud.update_customer(db, customer_id, customer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{customer_id}/")
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    try:
        crud.soft_delete_customer(db, customer_id, current_user.id)
        return {"message": "تم حذف العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_customers(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(admin_or_supervisor)):
    return crud.bulk_soft_delete_customers(db, payload.ids, current_user.id)