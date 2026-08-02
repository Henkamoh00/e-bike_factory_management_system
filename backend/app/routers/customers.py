from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, models
from ..security import require_tab

router = APIRouter(prefix="/api/customers", tags=["customers"])

can_access_customers = require_tab("customers")
can_view_archive = require_tab("archive")


@router.get("/")
def get_customers(db: Session = Depends(get_db), current_user: models.User = Depends(can_access_customers)):
    return crud.get_customers_with_sales(db)


@router.post("/")
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_customers)):
    # 🛡️ فحص التكرار يستثني العملاء المؤرشفين (is_deleted=True)
    # حتى لا يبقى اسم العميل "محجوزًا للأبد" بعد الحذف الناعم — نفس سلوك Worker/BikeType/BikeColor
    existing = db.query(models.Customer).filter(
        models.Customer.name == customer.name,
        models.Customer.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="العميل موجود مسبقاً")
    return crud.create_customer(db, customer, current_user.id)


@router.put("/{customer_id}/")
def update_customer(customer_id: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_customers)):
    try:
        return crud.update_customer(db, customer_id, customer, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{customer_id}/")
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_customers)):
    try:
        crud.soft_delete_customer(db, customer_id, current_user.id)
        return {"message": "تم حذف العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/bulk-delete/", response_model=schemas.BulkActionResult)
def bulk_delete_customers(payload: schemas.BulkIds, db: Session = Depends(get_db), current_user: models.User = Depends(can_access_customers)):
    return crud.bulk_soft_delete_customers(db, payload.ids, current_user.id)


@router.get("/archived/", response_model=list[schemas.ArchivedCustomerResponse])
def get_archived_customers(db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    return crud.get_archived_customers(db)


@router.post("/{customer_id}/restore/")
def restore_customer(customer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(can_view_archive)):
    try:
        crud.restore_customer(db, customer_id, current_user.id)
        return {"message": "تم استعادة العميل بنجاح", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))