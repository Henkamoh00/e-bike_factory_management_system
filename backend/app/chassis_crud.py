from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from . import models, assembly_crud, faults_crud


def get_available_chassis(db: Session):
    sold_numbers = {
        s[0] for s in db.query(models.Sale.chassis_number)
        .filter(models.Sale.status == "active")
        .all()
    }

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
        and chassis_number not in sold_numbers
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

# 📌 راجع backend/NOTES.md — قسم "دالة get_chassis_summary معقّدة (complexity=18)"
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
    """
    🆕 مُصفَّحة ومُفلتَرة من جهة السيرفر الآن.
    ملاحظة: البيانات مُجمَّعة (aggregated) من سجلات التجميع، لذا يتم بناء
    الملخص الكامل أولاً بالذاكرة ثم تُطبَّق الفلاتر والتصفيح على النتيجة،
    لأن التجميع (حسب رقم الهيكل) لا يمكن أن يتم مباشرة عبر offset/limit في SQL
    بسبب طبيعة العلاقة (سجل واحد أو أكثر لكل هيكل).
    """
    all_records = db.query(models.AssemblyRecord).all()
    records_by_chassis = {}
    for r in all_records:
        records_by_chassis.setdefault(r.chassis_number, []).append(r)

    active_sold_map = {
        s.chassis_number: s
        for s in db.query(models.Sale)
        .options(joinedload(models.Sale.customer))
        .filter(models.Sale.status == "active")
        .all()
    }

    all_faults = db.query(models.Fault).all()
    faults_by_chassis = {}
    for f in all_faults:
        faults_by_chassis.setdefault(f.chassis_number, []).append(f)

    summary = []
    for chassis_num, records in records_by_chassis.items():
        is_complete = assembly_crud.is_chassis_complete(records)
        sale = active_sold_map.get(chassis_num)
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

        summary.append({
            "chassis_number": chassis_num,
            "is_complete": is_complete,
            "is_sold": sale is not None,
            "workers": worker_names,
            "stages": stage_values,
            "stage_workers": stage_workers,
            "bike_type": bike_type_name,
            "bike_color": bike_color_name,
            "customer_name": sale.customer.name if sale and sale.customer else None,
            "pending_faults_count": len(pending_faults),
            "total_faults_count": len(faults),
            "last_updated": max(r.timestamp for r in records),
        })

    # ── تطبيق الفلاتر (بنفس منطق الفرونت إند القديم) ──────────────────
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

    sales = (
        db.query(models.Sale)
        .filter(
            models.Sale.chassis_number == chassis_number
        )
        .order_by(desc(models.Sale.sale_date))
        .all()
    )

    for sale in sales:
        sale.customer_name = sale.customer.name if sale.customer else "غير معروف"

    faults = faults_crud.get_faults_by_chassis(
        db,
        chassis_number
    )

    bike_type_name = next((r.bike_type.name for r in assembly_records if r.bike_type), None)
    bike_color_name = next((r.bike_color.name for r in assembly_records if r.bike_color), None)

    return {
        "chassis_number": chassis_number,
        "assembly_history": assembly_records,
        "sales": sales,
        "faults": faults,
        "bike_type": bike_type_name,
        "bike_color": bike_color_name,
    }
