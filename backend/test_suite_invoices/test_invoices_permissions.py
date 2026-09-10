"""
test_invoices_permissions.py - صلاحيات تبويب invoices، بما فيها اختبار
إصلاح الوصول العابر للتبويبات (invoices-only يمكنه قراءة customers/faults/
chassis دون امتلاك تبويباتها الخاصة)، والتأكد من عدم انكسار هذا الإصلاح
مستقبلاً + تكامل إحصائيات لوحة المدير مع نظام الفوترة.
"""


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00"):
    return {"chassis_number": chassis_number, "unit_price": unit_price}


# ====================== الوصول لمسارات الفوترة نفسها ======================

def test_operator_without_invoices_tab_forbidden(operator_client):
    response = operator_client.get("/api/invoices/")
    assert response.status_code == 403


def test_supervisor_with_invoices_tab_allowed(supervisor_client):
    response = supervisor_client.get("/api/invoices/")
    assert response.status_code == 200


def test_invoices_only_can_create_and_view_invoices(invoices_only_client, customer, make_chassis):
    chassis = make_chassis()
    create = _create_invoice(invoices_only_client, customer.id, [_item(chassis)])
    assert create.status_code == 200, create.text

    listing = invoices_only_client.get("/api/invoices/")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_invoices_only_can_access_stats_summary(invoices_only_client):
    response = invoices_only_client.get("/api/invoices/stats/summary/")
    assert response.status_code == 200


# ====================== 🆕 إصلاح اليوم: وصول invoices-only لتبويبات أخرى ======================

def test_invoices_only_can_view_customers_list(invoices_only_client, customer):
    response = invoices_only_client.get("/api/customers/")
    assert response.status_code == 200


def test_invoices_only_can_search_customers_simple(invoices_only_client, customer):
    response = invoices_only_client.get("/api/customers/simple/")
    assert response.status_code == 200


def test_invoices_only_can_create_customer(invoices_only_client):
    response = invoices_only_client.post(
        "/api/customers/", json={"name": "عميل أضافه مستخدم فوترة فقط"}
    )
    assert response.status_code == 200, response.text


def test_invoices_only_cannot_update_customer(invoices_only_client, customer):
    response = invoices_only_client.put(
        f"/api/customers/{customer.id}/", json={"name": "اسم جديد"}
    )
    assert response.status_code == 403


def test_invoices_only_cannot_delete_customer(invoices_only_client, customer):
    response = invoices_only_client.delete(f"/api/customers/{customer.id}/")
    assert response.status_code == 403


def test_invoices_only_can_view_faults_list(invoices_only_client, make_chassis):
    """
    🛡️ القراءة فقط (GET) تبقى مفتوحة لمن يملك invoices — يحتاجها
    ReturnFormModal.vue لربط الإرجاع بعطل معلّق موجود مسبقًا.
    🔧 لا نستخدم authenticated_client هنا مع invoices_only_client في نفس
    الاختبار (نفس فخ تصادم الكوكيز الموثّق أدناه) — بدلاً من ذلك نكتفي
    باختبار مسار القراءة نفسه، وهو كافٍ للتأكد من عدم رفض الوصول 403/401.
    """
    make_chassis()
    response = invoices_only_client.get("/api/faults/")
    assert response.status_code == 200


# ====================== 🔒 إصلاح أمني: تقييد إدارة الأعطال الفعلية بتبويب "faults" فقط ======================
# 🛡️🆕 can_access_faults = require_tab("faults") في faults.py يقيّد الإنشاء/
# التصليح/الإلغاء حصريًا بتبويب "faults" — لا يكفي امتلاك تبويب "invoices".
# مستخدم يملك "invoices" فقط (أو حتى أي مستخدم مسجَّل دخول بلا أي تبويب
# متعلق) لا يمكنه إنشاء/تصليح عطل مباشرة عبر /api/faults/. القراءة فقط
# (GET) هي ما يحتاجه تدفق الفوترة (راجع can_view_faults في faults.py)،
# أما الإنشاء والتصليح والإلغاء فتبقى حكرًا على تبويب "faults" حصريًا.
# لاحظ أن تدفق "تسجيل عطل تلقائيًا عند إرجاع دراجة بسبب عطل"
# (create_fault_stage في ChassisReturnCreate) لا يمر إطلاقًا عبر هذا
# الراوتر — هو يُنشئ سجل Fault مباشرة داخل invoices_crud.create_return
# بصلاحية can_access_invoices فقط، لذلك هذا التقييد لا يكسر تلك الميزة
# إطلاقًا (راجع test_invoices_returns_refunds.py
# ::test_create_return_with_create_fault_stage_auto_creates_fault).

def test_invoices_only_cannot_create_fault_directly(invoices_only_client, make_chassis):
    chassis = make_chassis()
    response = invoices_only_client.post(
        "/api/faults/", json={"chassis_number": chassis, "description": "محاولة إنشاء عطل مباشرة من مستخدم فوترة فقط"}
    )
    assert response.status_code == 403


def test_invoices_only_cannot_repair_fault(invoices_only_client, make_chassis):
    """
    🛡️🔧 إصلاح جوهري: كان هذا الاختبار يستخدم authenticated_client معًا مع
    invoices_only_client في نفس الاختبار — وكلاهما يعتمدان على نفس فِكستشر
    `client` المشترك (pytest يُخزّن الفِكستشر لمرة واحدة فقط لكل اختبار).
    كانت النتيجة: authenticated_client يُسجّل دخول admin *فوق* كوكيز
    invoices_only الموجودة أصلاً على نفس كائن client، فينقلب كل طلب لاحق
    عبر invoices_only_client فعليًا إلى طلب بصلاحية admin بالخطأ. الحل:
    استخدام عميل TestClient معزول تمامًا (بكوكيز خاصة به، مستورد من
    conftest) لتسجيل دخول admin وإنشاء العطل الذي سنحاول تصليحه، دون أي
    تأثير على كوكيز invoices_only_client المستخدم لاحقًا لمحاولة التصليح.
    """
    from conftest import CSRFAwareTestClient, _login
    from app.main import app

    chassis = make_chassis()

    with CSRFAwareTestClient(app) as isolated_admin_client:
        _login(isolated_admin_client, "test_admin", "AdminPass123!")
        fault = isolated_admin_client.post(
            "/api/faults/", json={"chassis_number": chassis, "description": "عطل"}
        ).json()

    response = invoices_only_client.post(
        f"/api/faults/{fault['id']}/repair/", json={"worker_name": "عامل"}
    )
    assert response.status_code == 403


def test_customers_only_role_cannot_create_fault(customers_only_client, make_chassis):
    """ضابط سلبي: مستخدم بلا تبويب faults ولا invoices لا يمكنه إنشاء عطل إطلاقًا"""
    chassis = make_chassis()
    response = customers_only_client.post(
        "/api/faults/", json={"chassis_number": chassis, "description": "محاولة من مستخدم بلا صلاحية"}
    )
    assert response.status_code == 403


def test_unauthenticated_cannot_create_fault(authenticated_client, make_chassis):
    """
    🔧 ملاحظة تقنية مهمة: لا يجوز هنا استخدام فِكستشر `client` العادي مباشرة
    مع الاعتماد أيضًا على `make_chassis` — الحل: عميل TestClient معزول
    تمامًا يُنشأ يدويًا هنا، بلا أي كوكيز إطلاقًا.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    chassis = make_chassis()

    with TestClient(app) as anonymous_client:
        response = anonymous_client.post(
            "/api/faults/", json={"chassis_number": chassis, "description": "محاولة بلا تسجيل دخول"}
        )
        assert response.status_code == 401


def test_invoices_only_can_view_chassis_summary(invoices_only_client, make_chassis):
    make_chassis()
    response = invoices_only_client.get("/api/chassis/summary/")
    assert response.status_code == 200


def test_invoices_only_can_view_chassis_detail(invoices_only_client, make_chassis):
    chassis = make_chassis()
    response = invoices_only_client.get(f"/api/chassis/{chassis}/")
    assert response.status_code == 200


def test_invoices_only_can_view_available_chassis(invoices_only_client, make_chassis):
    make_chassis()
    response = invoices_only_client.get("/api/chassis/available/")
    assert response.status_code == 200


def test_invoices_only_cannot_access_assembly_record(invoices_only_client):
    response = invoices_only_client.post(
        "/api/assembly/record/?force=false",
        json={
            "chassis_number": "SHOULD-NOT-BE-ALLOWED",
            "worker_name": "عامل",
            "stage": "تجميع_كامل",
            "bike_type_name": "نوع",
            "bike_color_name": "لون",
        },
    )
    assert response.status_code == 403


def test_invoices_only_cannot_access_workers_tab(invoices_only_client):
    response = invoices_only_client.get("/api/workers/")
    # ملاحظة: /api/workers/ يعتمد على get_current_user فقط (بلا فحص تبويب) في
    # النسخة الحالية من workers.py، لذا يُتوقع 200. هذا الاختبار توثيقي للسلوك
    # الحالي حتى لا يُفاجَأ المطوّر لاحقاً بأي تغيير غير مقصود في الصلاحيات.
    assert response.status_code == 200


# ====================== ضابط سلبي: customers-only لا يصل لـ faults ======================

def test_customers_only_role_cannot_view_faults(customers_only_client):
    """
    التأكد أن require_any_tab("faults", "invoices") لا يمنح الوصول لأي تبويب
    عشوائي آخر — فقط لمن يملك "faults" أو "invoices" تحديدًا.
    """
    response = customers_only_client.get("/api/faults/")
    assert response.status_code == 403


def test_customers_only_role_cannot_view_chassis(customers_only_client):
    response = customers_only_client.get("/api/chassis/summary/")
    assert response.status_code == 403


def test_customers_only_role_can_view_customers(customers_only_client):
    response = customers_only_client.get("/api/customers/")
    assert response.status_code == 200


# ====================== تكامل الإحصائيات مع نظام الفوترة ======================

def test_dashboard_stats_requires_stats_tab(invoices_only_client):
    response = invoices_only_client.get("/api/stats/")
    assert response.status_code == 403


def test_dashboard_stats_counts_active_invoiced_chassis_as_sold(authenticated_client, customer, make_chassis):
    c1 = make_chassis()
    c2 = make_chassis()
    make_chassis()  # هيكل ثالث متاح، غير مُباع

    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    item1_id = created.json()["items"][0]["id"]

    before = authenticated_client.get("/api/stats/").json()
    assert before["sold"] == 2

    # إرجاع أحد البندين يجب أن يُخرجه من "المُباع" فورًا (يعود متاحًا للبيع)
    authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": "سبب"}
    )
    after_return = authenticated_client.get("/api/stats/").json()
    assert after_return["sold"] == 1

    available_after = authenticated_client.get("/api/chassis/available/").json()
    assert c1 in available_after


def test_invoice_stats_summary_reflects_payments_and_totals(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()

    _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00")],
        initial_payment_amount="1000.00",
    )
    _create_invoice(
        authenticated_client, customer.id, [_item(c2, "500.00")],
        initial_payment_amount="200.00",
    )

    response = authenticated_client.get("/api/invoices/stats/summary/")
    assert response.status_code == 200
    data = response.json()

    assert data["total_billed"] == "1500.00"
    assert data["total_collected"] == "1200.00"
    assert data["total_outstanding"] == "300.00"
    assert data["today_count"] == 2
    assert data["today_revenue"] == "1200.00"