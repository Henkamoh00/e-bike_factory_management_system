from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, assembly_crud
from invoicing import models as invoicing_models


def get_dashboard_stats(db: Session):
    all_records = db.query(models.AssemblyRecord).all()

    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    total_chassis = len(records_by_chassis)

    completed = sum(
        1 for records in records_by_chassis.values()
        if assembly_crud.is_chassis_complete(records)
    )

    # 🆕🛡️ "تم بيعها" أصبح يُحسب من نظام الفوترة (بند فاتورة نشط على فاتورة
    # غير ملغاة وغير مُرجَع) بدل جدول sales القديم الذي أُزيل نهائيًا —
    # هذا هو سبب عدم ظهور الدراجات المباعة حديثًا في هذا الكارد سابقًا
    sold = (
        db.query(invoicing_models.InvoiceItem)
        .join(invoicing_models.Invoice)
        .outerjoin(
            invoicing_models.ChassisReturn,
            invoicing_models.ChassisReturn.invoice_item_id == invoicing_models.InvoiceItem.id
        )
        .filter(
            invoicing_models.Invoice.status != "cancelled",
            invoicing_models.Invoice.is_deleted == False,
            invoicing_models.ChassisReturn.id.is_(None),
        )
        .count()
    )

    pending_faults = db.query(func.count(models.Fault.id)).filter(
        models.Fault.status == "pending"
    ).scalar() or 0

    return {
        "total_chassis": total_chassis,
        "completed": completed,
        "in_progress": total_chassis - completed,
        "sold": sold,
        "pending_faults": pending_faults
    }