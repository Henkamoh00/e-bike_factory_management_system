"""
test_chassis_summary.py - اختبارات توصيفية (characterization) لـ GET /api/chassis/summary/
(chassis_crud.get_chassis_summary): كل فلتر على حدة ومجتمعة، والصفحات، وحقول الصف.
تحمي منطق التجميع (aggregation) عند أي إعادة هيكلة أو إضافة فلتر جديد.
"""
from app.assembly_crud import STAGE_ASSEMBLY, STAGE_COVER, STAGE_COMPLETE

TYPE_A, TYPE_B = "نوع ألف", "نوع باء"
COLOR_RED, COLOR_BLUE = "أحمر", "أزرق"
W1, W2, W3, W4 = "عامل 1", "عامل 2", "عامل 3", "عامل 4"


def _record(client, chassis, stage, worker, bike_type=None, bike_color=None):
    payload = {"chassis_number": chassis, "worker_name": worker, "stage": stage}
    if bike_type:
        payload["bike_type_name"] = bike_type
    if bike_color:
        payload["bike_color_name"] = bike_color
    response = client.post("/api/assembly/record/?force=false", json=payload)
    assert response.status_code == 200, response.text


def _summary(client, **params):
    response = client.get("/api/chassis/summary/", params={"limit": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()


def _numbers(data):
    return [row["chassis_number"] for row in data["items"]]


class _World:
    """5 هياكل بحالات مختلفة: متاح / مباع / قيد التجميع / مرحلتان / به عطل."""


def _build_world(client, customer, make_chassis):
    world = _World()
    world.available = make_chassis(bike_type_name=TYPE_A, bike_color_name=COLOR_RED, worker_name=W1)
    world.sold = make_chassis(bike_type_name=TYPE_B, bike_color_name=COLOR_BLUE, worker_name=W2)
    world.faulty = make_chassis(bike_type_name=TYPE_A, bike_color_name=COLOR_BLUE, worker_name=W1)

    world.progress = "CUSTOM-PROGRESS"
    _record(client, world.progress, STAGE_ASSEMBLY, W3, bike_type=TYPE_A)

    world.two_stage = "CUSTOM-TWO-STAGES"
    _record(client, world.two_stage, STAGE_ASSEMBLY, W3, bike_type=TYPE_B)
    _record(client, world.two_stage, STAGE_COVER, W4, bike_color=COLOR_RED)

    invoice = client.post(
        "/api/invoices/",
        json={"customer_id": customer.id, "items": [{"chassis_number": world.sold, "unit_price": "1000.00"}]},
    )
    assert invoice.status_code == 200, invoice.text

    fault = client.post("/api/faults/", json={"chassis_number": world.faulty, "description": "عطل تجريبي"})
    assert fault.status_code == 200, fault.text
    return world


def test_summary_without_filters_lists_all_sorted(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    data = _summary(authenticated_client)
    assert data["total"] == 5
    assert _numbers(data) == sorted([w.available, w.sold, w.faulty, w.progress, w.two_stage])


def test_summary_row_fields(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    rows = {r["chassis_number"]: r for r in _summary(authenticated_client)["items"]}

    sold = rows[w.sold]
    assert sold["is_complete"] is True
    assert sold["is_sold"] is True
    assert sold["customer_name"] == customer.name
    assert sold["bike_type"] == TYPE_B
    assert sold["bike_color"] == COLOR_BLUE
    assert sold["workers"] == [W2]
    assert sold["stages"] == [STAGE_COMPLETE]
    assert sold["stage_workers"] == {STAGE_COMPLETE: W2}

    two = rows[w.two_stage]
    assert two["is_complete"] is True
    assert two["is_sold"] is False
    assert two["customer_name"] is None
    assert sorted(two["workers"]) == sorted([W3, W4])
    assert two["stage_workers"] == {STAGE_ASSEMBLY: W3, STAGE_COVER: W4}
    assert two["bike_type"] == TYPE_B
    assert two["bike_color"] == COLOR_RED

    progress = rows[w.progress]
    assert progress["is_complete"] is False
    assert progress["bike_color"] is None

    faulty = rows[w.faulty]
    assert faulty["pending_faults_count"] == 1
    assert faulty["total_faults_count"] == 1
    assert rows[w.available]["pending_faults_count"] == 0
    assert rows[w.available]["last_updated"] is not None


def test_summary_status_filters(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)

    available = set(_numbers(_summary(authenticated_client, status="available")))
    assert available == {w.available, w.faulty, w.two_stage}

    assert _numbers(_summary(authenticated_client, status="sold")) == [w.sold]
    assert _numbers(_summary(authenticated_client, status="in_progress")) == [w.progress]
    assert _numbers(_summary(authenticated_client, status="has_fault")) == [w.faulty]


def test_summary_chassis_number_filter_is_case_insensitive_substring(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    data = _summary(authenticated_client, chassis_number="custom-")
    assert set(_numbers(data)) == {w.progress, w.two_stage}
    assert data["total"] == 2


def test_summary_worker_filter_any_stage(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    assert set(_numbers(_summary(authenticated_client, worker_name=W1))) == {w.available, w.faulty}
    assert set(_numbers(_summary(authenticated_client, worker_name=W3))) == {w.progress, w.two_stage}
    assert _numbers(_summary(authenticated_client, worker_name=W4)) == [w.two_stage]
    assert _numbers(_summary(authenticated_client, worker_name="لا أحد")) == []


def test_summary_stage_filter(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    assert set(_numbers(_summary(authenticated_client, stage=STAGE_COMPLETE))) == {w.available, w.sold, w.faulty}
    assert set(_numbers(_summary(authenticated_client, stage=STAGE_ASSEMBLY))) == {w.progress, w.two_stage}
    assert _numbers(_summary(authenticated_client, stage=STAGE_COVER)) == [w.two_stage]


def test_summary_worker_and_stage_direct_match(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    assert _numbers(_summary(authenticated_client, worker_name=W4, stage=STAGE_COVER)) == [w.two_stage]
    # W4 لم يقم بمرحلة تجميع_الهيكل
    assert _numbers(_summary(authenticated_client, worker_name=W4, stage=STAGE_ASSEMBLY)) == []


def test_summary_worker_and_stage_covered_by_full_assembly(authenticated_client, customer, make_chassis):
    """عامل نفّذ (تجميع_كامل) يُحتسب عاملًا على مرحلتَي الهيكل والكهرباء معًا."""
    w = _build_world(authenticated_client, customer, make_chassis)
    for stage in (STAGE_ASSEMBLY, STAGE_COVER):
        assert set(_numbers(_summary(authenticated_client, worker_name=W1, stage=stage))) == {w.available, w.faulty}
    # لكن ليس على مرحلة "تجميع_كامل" نفسها بأي عامل آخر
    assert _numbers(_summary(authenticated_client, worker_name=W3, stage=STAGE_COMPLETE)) == []


def test_summary_bike_type_and_color_filters(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    assert set(_numbers(_summary(authenticated_client, bike_type=TYPE_A))) == {w.available, w.faulty, w.progress}
    assert set(_numbers(_summary(authenticated_client, bike_type=TYPE_B))) == {w.sold, w.two_stage}
    assert set(_numbers(_summary(authenticated_client, bike_color=COLOR_BLUE))) == {w.sold, w.faulty}
    assert set(_numbers(_summary(authenticated_client, bike_color=COLOR_RED))) == {w.available, w.two_stage}


def test_summary_combined_filters(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    data = _summary(authenticated_client, status="available", bike_type=TYPE_A, bike_color=COLOR_BLUE)
    assert _numbers(data) == [w.faulty]
    assert _numbers(_summary(authenticated_client, status="sold", bike_type=TYPE_A)) == []


def test_summary_pagination(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    everything = sorted([w.available, w.sold, w.faulty, w.progress, w.two_stage])

    first = _summary(authenticated_client, skip=0, limit=2)
    second = _summary(authenticated_client, skip=2, limit=2)
    last = _summary(authenticated_client, skip=4, limit=2)
    assert first["total"] == second["total"] == last["total"] == 5
    assert _numbers(first) + _numbers(second) + _numbers(last) == everything


def test_summary_returned_chassis_is_not_sold(authenticated_client, customer, make_chassis):
    w = _build_world(authenticated_client, customer, make_chassis)
    invoice = authenticated_client.get("/api/invoices/").json()["items"][0]
    item_id = invoice["items"][0]["id"]
    authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": "الدراجة مكسورة"}
    )

    rows = {r["chassis_number"]: r for r in _summary(authenticated_client)["items"]}
    assert rows[w.sold]["is_sold"] is False
    assert w.sold in _numbers(_summary(authenticated_client, status="available"))


def test_summary_requires_one_of_the_allowed_tabs(customers_only_client):
    assert customers_only_client.get("/api/chassis/summary/").status_code == 403
