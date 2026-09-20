"""
test_assembly.py - تسجيل مراحل التجميع بحسب رقم الشاسيه
المسار الفعلي: POST /api/assembly/record/?force=true|false
المراحل (AssemblyStage): تجميع_الهيكل / توصيل_الكهرباء_والغلاف / تجميع_كامل

ملاحظة: راوتر assembly.py يُعبّئ في الاستجابة worker_name و bike_type_name
و bike_color_name و recorded_by_username من العلاقات (لا تُخزَّن في السجل نفسه).
"""
from app.assembly_crud import STAGE_ASSEMBLY, STAGE_COVER, STAGE_COMPLETE
from app import models

CHASSIS = "TEST-CHASSIS-0001"


def _register(client, chassis_number, stage, worker_name, force=False,
              bike_type_name=None, bike_color_name=None):
    payload = {
        "chassis_number": chassis_number,
        "worker_name": worker_name,
        "stage": stage,
    }
    if bike_type_name:
        payload["bike_type_name"] = bike_type_name
    if bike_color_name:
        payload["bike_color_name"] = bike_color_name
    return client.post(
        f"/api/assembly/record/?force={'true' if force else 'false'}",
        json=payload,
    )


def test_register_assembly_stage_success(authenticated_client, db_session):
    response = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل الهيكل",
        bike_type_name="نوع تجريبي",
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chassis_number"] == CHASSIS
    assert data["stage"] == STAGE_ASSEMBLY
    assert data["worker_name"] == "عامل الهيكل"
    assert data["bike_type_name"] == "نوع تجريبي"
    assert data["bike_color_name"] is None  # اللون لا يُسجَّل في مرحلة تجميع الهيكل
    assert data["recorded_by_username"] == "test_admin"

    record = (
        db_session.query(models.AssemblyRecord)
        .filter_by(chassis_number=CHASSIS, stage=STAGE_ASSEMBLY)
        .first()
    )
    assert record is not None
    assert record.worker is not None
    assert record.worker.name == "عامل الهيكل"


def test_register_stage_missing_required_bike_type_rejected(authenticated_client):
    """مرحلة تجميع_الهيكل بدون bike_type_name يجب أن تُرفض (422)."""
    response = _register(authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل الهيكل")
    assert response.status_code == 422


def test_register_cover_before_assembly_rejected(authenticated_client):
    """لا يمكن تسجيل توصيل_الكهرباء_والغلاف قبل تجميع_الهيكل."""
    response = _register(
        authenticated_client, CHASSIS, STAGE_COVER, "عامل الكهرباء",
        bike_color_name="أحمر",
    )
    assert response.status_code == 422


def test_register_same_stage_different_worker_rejected_without_force(authenticated_client):
    first = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل أول",
        bike_type_name="نوع تجريبي",
    )
    assert first.status_code == 200

    second = _register(authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل ثاني")
    assert second.status_code == 409
    assert second.headers.get("x-confirm-required") == "true"


def test_register_same_stage_with_force_accepted(authenticated_client, db_session):
    first = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل أول",
        bike_type_name="نوع تجريبي",
    )
    assert first.status_code == 200

    second = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل ثاني", force=True
    )
    assert second.status_code == 200

    record = (
        db_session.query(models.AssemblyRecord)
        .filter_by(chassis_number=CHASSIS, stage=STAGE_ASSEMBLY)
        .first()
    )
    assert record is not None
    assert record.worker.name == "عامل ثاني"


def test_register_same_stage_same_worker_updates_timestamp_without_conflict(authenticated_client):
    """نفس المرحلة بنفس العامل مجددًا لا تُعتبر تعارضًا حتى بدون force."""
    first = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل أول",
        bike_type_name="نوع تجريبي",
    )
    assert first.status_code == 200

    second = _register(authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل أول")
    assert second.status_code == 200


def test_register_stage_after_complete_rejected(authenticated_client):
    """بعد تسجيل مرحلة (تجميع_كامل)، أي مرحلة أخرى لنفس الهيكل تُرفض."""
    final = _register(
        authenticated_client, CHASSIS, STAGE_COMPLETE, "عامل شامل",
        bike_type_name="نوع تجريبي", bike_color_name="أزرق",
    )
    assert final.status_code == 200

    after = _register(authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل آخر")
    assert after.status_code == 409


def test_register_complete_after_assembly_rejected(authenticated_client):
    """لا يمكن تسجيل تجميع_كامل لهيكل يملك سجل تجميع_الهيكل مسبقًا."""
    assembly = _register(
        authenticated_client, CHASSIS, STAGE_ASSEMBLY, "عامل الهيكل",
        bike_type_name="نوع تجريبي",
    )
    assert assembly.status_code == 200

    complete = _register(
        authenticated_client, CHASSIS, STAGE_COMPLETE, "عامل شامل",
        bike_color_name="أزرق",
    )
    assert complete.status_code == 409


def test_operator_with_assembly_tab_can_register(operator_client):
    """عامل operator (يملك تبويب assembly ضمن seed_roles) يُسمح له بالتسجيل."""
    response = _register(
        operator_client, "TEST-CHASSIS-OP-0001", STAGE_ASSEMBLY, "عامل مشغل",
        bike_type_name="نوع تجريبي",
    )
    assert response.status_code == 200


def test_unauthenticated_cannot_register(client):
    response = _register(client, CHASSIS, STAGE_ASSEMBLY, "عامل", bike_type_name="نوع")
    assert response.status_code == 401
