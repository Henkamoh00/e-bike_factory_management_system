from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from . import models, assembly_crud, faults_crud
from invoicing import models as invoicing_models


def _get_active_invoiced_chassis_numbers(db: Session) -> set:
    """
    🛡️ الهياكل التي عليها فعليًا بند فاتورة نشط (غير ملغى، وغير مُرجَع).
    هذا هو المصدر الوحيد الآن لتحديد "المُباع" بعد حذف نظام sales القديم.
    """
    active_items = (
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
        .all()
    )
    return {item.chassis_number for item in active_items}


def get_available_chassis(db: Session):
    invoiced_numbers = _get_active_invoiced_chassis_numbers(db)

    faulty_numbers = {
        f[0] for f in db.query(models.Fault.chassis_number)
        .filter(models.Fault.status == "pending")
        .distinct()
        .all()
    }

    all_records = db.query(models.AssemblyRecord).all()

    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    available = [
        chassis_number
        for chassis_number, records in records_by_chassis.items()
        if assembly_crud.is_chassis_complete(records)
        and chassis_number not in invoiced_numbers
        and chassis_number not in faulty_numbers
    ]

    return sorted(available)


def get_all_chassis_numbers(db: Session):
    chassis_numbers = (
        db.query(models.AssemblyRecord.chassis_number)
        .distinct()
        .order_by(models.AssemblyRecord.chassis_number)
        .all()
    )
    return [c[0] for c in chassis_numbers]


def get_chassis_summary(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    chassis_number: str | None = None,
    status: str | None = None,
    worker_name: str | None = None,
    stage: str | None = None,
    bike_type: str | None = None,
    bike_color: str | None = None,
):
    all_records = db.query(models.AssemblyRecord).all()
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    # 🆕 "المُباع" الآن مصدره الوحيد نظام الفوترة (بعد حذف sales القديم)
    active_items = (
        db.query(invoicing_models.InvoiceItem)
        .join(invoicing_models.Invoice)
        .outerjoin(
            invoicing_models.ChassisReturn,
            invoicing_models.ChassisReturn.invoice_item_id == invoicing_models.InvoiceItem.id
        )
        .options(joinedload(invoicing_models.InvoiceItem.invoice).joinedload(invoicing_models.Invoice.customer))
        .filter(
            invoicing_models.Invoice.status != "cancelled",
            invoicing_models.Invoice.is_deleted == False,
            invoicing_models.ChassisReturn.id.is_(None),
        )
        .all()
    )
    invoiced_map = {item.chassis_number: item.invoice for item in active_items}

    all_faults = db.query(models.Fault).all()
    faults_by_chassis = {}
    for f in all_faults:
        faults_by_chassis.setdefault(f.chassis_number, []).append(f)

    summary = []
    for chassis_num, records in records_by_chassis.items():
        is_complete = assembly_crud.is_chassis_complete(records)
        invoice = invoiced_map.get(chassis_num)
        faults = faults_by_chassis.get(chassis_num, [])
        pending_faults = [f for f in faults if f.status == "pending"]

        worker_names = list({r.worker.name for r in records if r.worker})
        stage_values = list({r.stage.value if hasattr(r.stage, 'value') else r.stage for r in records})
        bike_type_name = next((r.bike_type.name for r in records if r.bike_type), None)
        bike_color_name = next((r.bike_color.name for r in records if r.bike_color), None)

        stage_workers = {
            (r.stage.value if hasattr(r.stage, 'value') else r.stage): (r.worker.name if r.worker else None)
            for r in records
        }

        customer_name = invoice.customer.name if invoice and invoice.customer else None

        summary.append({
            "chassis_number": chassis_num,
            "is_complete": is_complete,
            "is_sold": invoice is not None,
            "workers": worker_names,
            "stages": stage_values,
            "stage_workers": stage_workers,
            "bike_type": bike_type_name,
            "bike_color": bike_color_name,
            "customer_name": customer_name,
            "pending_faults_count": len(pending_faults),
            "total_faults_count": len(faults),
            "last_updated": max(r.timestamp for r in records),
        })

    def matches(item):
        if chassis_number and chassis_number.lower() not in item["chassis_number"].lower():
            return False
        if status == "available" and (not item["is_complete"] or item["is_sold"]):
            return False
        if status == "sold" and not item["is_sold"]:
            return False
        if status == "in_progress" and item["is_complete"]:
            return False
        if status == "has_fault" and item["pending_faults_count"] == 0:
            return False

        stage_workers = item["stage_workers"]
        if worker_name and stage:
            direct_match = stage_workers.get(stage) == worker_name
            covered_by_full = (
                stage in (assembly_crud.STAGE_ASSEMBLY, assembly_crud.STAGE_COVER)
                and stage_workers.get(assembly_crud.STAGE_COMPLETE) == worker_name
            )
            if not direct_match and not covered_by_full:
                return False
        elif worker_name:
            if worker_name not in item["workers"]:
                return False
        elif stage:
            if stage not in item["stages"]:
                return False

        if bike_type and item["bike_type"] != bike_type:
            return False
        if bike_color and item["bike_color"] != bike_color:
            return False
        return True

    filtered = [s for s in summary if matches(s)]
    filtered.sort(key=lambda x: x["chassis_number"])

    total = len(filtered)
    paginated = filtered[skip:skip + limit]
    return paginated, total


def get_full_chassis_history(db: Session, chassis_number: str):

    assembly_records = assembly_crud.get_assembly_by_chassis(
        db,
        chassis_number
    )

    for record in assembly_records:
        if record.worker:
            record.worker_name = record.worker.name
        else:
            record.worker_name = "غير معروف"

    # 🆕🛡️ سجل البيع الآن مبني بالكامل على نظام الفوترة بدل جدول sales
    # القديم الذي أُزيل نهائيًا. نجلب كل بنود الفواتير الخاصة بهذا الهيكل عبر
    # كل تاريخه (حتى الملغاة/المُرجَعة، حفاظًا على الأثر الكامل)، ونحدد حالة
    # كل بند: نشط (active) / مُرجَع (returned) / على فاتورة ملغاة (cancelled)
    items = (
        db.query(invoicing_models.InvoiceItem)
        .join(invoicing_models.Invoice)
        .options(
            joinedload(invoicing_models.InvoiceItem.invoice).joinedload(invoicing_models.Invoice.customer),
            joinedload(invoicing_models.InvoiceItem.invoice).joinedload(invoicing_models.Invoice.created_by),
            joinedload(invoicing_models.InvoiceItem.chassis_return),
        )
        .filter(invoicing_models.InvoiceItem.chassis_number == chassis_number)
        .order_by(desc(invoicing_models.Invoice.invoice_date))
        .all()
    )

    sales_history = []
    for item in items:
        inv = item.invoice
        ret = item.chassis_return
        if ret is not None:
            item_status = "returned"
            cancel_reason = ret.reason
            cancelled_at = ret.created_at
            return_notes = ret.notes
        elif inv.status == "cancelled":
            item_status = "cancelled"
            cancel_reason = inv.cancel_reason
            cancelled_at = inv.cancelled_at
            return_notes = None
        else:
            item_status = "active"
            cancel_reason = None
            cancelled_at = None
            return_notes = None

        sales_history.append({
            "id": item.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "customer_name": inv.customer.name if inv.customer else "غير معروف",
            "sale_date": inv.invoice_date,
            "notes": item.notes,
            "status": item_status,
            "cancelled_at": cancelled_at,
            "cancel_reason": cancel_reason,
            "return_notes": return_notes,
            "created_by_username": inv.created_by.username if inv.created_by else None,
        })

    faults = faults_crud.get_faults_by_chassis(
        db,
        chassis_number
    )

    bike_type_name = next((r.bike_type.name for r in assembly_records if r.bike_type), None)
    bike_color_name = next((r.bike_color.name for r in assembly_records if r.bike_color), None)

    return {
        "chassis_number": chassis_number,
        "assembly_history": assembly_records,
        "sales": sales_history,
        "faults": faults,
        "bike_type": bike_type_name,
        "bike_color": bike_color_name,
    }