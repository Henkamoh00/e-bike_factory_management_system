from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from . import models, assembly_crud, faults_crud
from invoicing import models as invoicing_models


def _get_active_invoice_items(db: Session, with_customer: bool = False):
    """
    بنود الفواتير النشطة: فاتورة غير ملغاة وغير محذوفة، والبند غير مُرجَع.
    with_customer=True يجلب الفاتورة والعميل مسبقًا (joinedload) لتفادي N+1.
    """
    query = (
        db.query(invoicing_models.InvoiceItem)
        .join(invoicing_models.Invoice)
        .outerjoin(
            invoicing_models.ChassisReturn,
            invoicing_models.ChassisReturn.invoice_item_id == invoicing_models.InvoiceItem.id
        )
    )
    if with_customer:
        query = query.options(
            joinedload(invoicing_models.InvoiceItem.invoice).joinedload(invoicing_models.Invoice.customer)
        )
    return query.filter(
        invoicing_models.Invoice.status != "cancelled",
        invoicing_models.Invoice.is_deleted.is_(False),
        invoicing_models.ChassisReturn.id.is_(None),
    ).all()


def _get_active_invoiced_chassis_numbers(db: Session) -> set:
    return {item.chassis_number for item in _get_active_invoice_items(db)}


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


def _stage_value(stage):
    return stage.value if hasattr(stage, "value") else stage


def _group_by_chassis(rows) -> dict:
    grouped = {}
    for row in rows:
        grouped.setdefault(row.chassis_number, []).append(row)
    return grouped


def _build_summary_row(chassis_num: str, records: list, invoice, faults: list) -> dict:
    pending_faults = [f for f in faults if f.status == "pending"]
    return {
        "chassis_number": chassis_num,
        "is_complete": assembly_crud.is_chassis_complete(records),
        "is_sold": invoice is not None,
        "workers": list({r.worker.name for r in records if r.worker}),
        "stages": list({_stage_value(r.stage) for r in records}),
        "stage_workers": {_stage_value(r.stage): (r.worker.name if r.worker else None) for r in records},
        "bike_type": next((r.bike_type.name for r in records if r.bike_type), None),
        "bike_color": next((r.bike_color.name for r in records if r.bike_color), None),
        "customer_name": invoice.customer.name if invoice and invoice.customer else None,
        "pending_faults_count": len(pending_faults),
        "total_faults_count": len(faults),
        "last_updated": max(r.timestamp for r in records),
    }


def _matches_status(item: dict, status: str | None) -> bool:
    if status == "available":
        return item["is_complete"] and not item["is_sold"]
    if status == "sold":
        return item["is_sold"]
    if status == "in_progress":
        return not item["is_complete"]
    if status == "has_fault":
        return item["pending_faults_count"] > 0
    return True


def _matches_worker_and_stage(item: dict, worker_name: str | None, stage: str | None) -> bool:
    stage_workers = item["stage_workers"]
    if worker_name and stage:
        # العامل الذي نفّذ (تجميع_كامل) يُحتسب عاملًا على مرحلتَي الهيكل والكهرباء أيضًا
        covered_by_full = (
            stage in (assembly_crud.STAGE_ASSEMBLY, assembly_crud.STAGE_COVER)
            and stage_workers.get(assembly_crud.STAGE_COMPLETE) == worker_name
        )
        return stage_workers.get(stage) == worker_name or covered_by_full
    if worker_name:
        return worker_name in item["workers"]
    if stage:
        return stage in item["stages"]
    return True


def _matches_filters(
    item: dict,
    chassis_number: str | None,
    status: str | None,
    worker_name: str | None,
    stage: str | None,
    bike_type: str | None,
    bike_color: str | None,
) -> bool:
    if chassis_number and chassis_number.lower() not in item["chassis_number"].lower():
        return False
    if not _matches_status(item, status):
        return False
    if not _matches_worker_and_stage(item, worker_name, stage):
        return False
    if bike_type and item["bike_type"] != bike_type:
        return False
    if bike_color and item["bike_color"] != bike_color:
        return False
    return True


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
    records_by_chassis = _group_by_chassis(db.query(models.AssemblyRecord).all())
    faults_by_chassis = _group_by_chassis(db.query(models.Fault).all())

    invoiced_map = {
        item.chassis_number: item.invoice
        for item in _get_active_invoice_items(db, with_customer=True)
    }

    summary = [
        _build_summary_row(
            chassis_num, records, invoiced_map.get(chassis_num), faults_by_chassis.get(chassis_num, [])
        )
        for chassis_num, records in records_by_chassis.items()
    ]

    filtered = [
        s for s in summary
        if _matches_filters(s, chassis_number, status, worker_name, stage, bike_type, bike_color)
    ]
    filtered.sort(key=lambda x: x["chassis_number"])

    total = len(filtered)
    return filtered[skip:skip + limit], total


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
