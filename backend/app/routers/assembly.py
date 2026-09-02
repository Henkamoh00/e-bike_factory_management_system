from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, assembly_crud, models
from ..security import require_tab
from ..rate_limit import limiter, get_rate_limit_key

router = APIRouter(prefix="/api/assembly", tags=["assembly"])

can_manage_assembly = require_tab("assembly")

# 🛡️🆕 حد 200/يوم لكل مستخدم على تسجيل عمليات التجميع — مسار كتابة حساس
# (كل تسجيل يُنشئ سجل تجميع، وقد يُنشئ ضمنيًا عاملاً/نوع دراجة/لون دراجة جديد)
# كان بلا أي حد سابقًا رغم ذلك. الحد مرتبط بالمستخدم (user:{username}) وليس IP
# حتى لا يتشارك عدة عمال يعملون خلف نفس IP نفس السقف اليومي.
@router.post("/record/", response_model=schemas.AssemblyResponse)
@limiter.limit("200/day", key_func=get_rate_limit_key)
def create_assembly_record(
    request: Request,
    assembly: schemas.AssemblyCreate,
    force: bool = Query(default=False, description="تجاوز تحذير العامل المختلف بعد تأكيد المسؤول"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(can_manage_assembly)
):
    try:
        record = assembly_crud.create_assembly_record(
            db=db,
            assembly=assembly,
            current_user_id=current_user.id,
            force=force,
        )
        # 📌 worker_name يبقى None عمدًا هنا حاليًا
        # راجع backend/NOTES.md — قسم "worker_name دائمًا None في استجابة تسجيل التجميع"
        if record.recorded_by:
            record.recorded_by_username = record.recorded_by.username
        return record
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))