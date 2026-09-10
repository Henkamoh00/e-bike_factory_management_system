"""
conftest.py - بيئة اختبار معزولة بالكامل لاختبارات نظام الفوترة (invoicing).

هذا المجلد (test_suite_invoices/) مستقل تمامًا عن مجلد الاختبارات العام
(test_suite/): له قاعدة بيانات SQLite خاصة به، وقد لا يؤثر حذفه بالكامل
على أي جزء آخر من المشروع. يجب وضعه كمجلد شقيق لمجلد app/ و invoicing/
(أي داخل مجلد backend/ نفسه الذي يحوي هذين الحزمتين).
"""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) ضبط متغيرات البيئة الوهمية قبل أي استيراد لـ app (database.py و security.py
#    يرميان RuntimeError/ValueError لو DATABASE_URL أو JWT_SECRET_KEY غير موجودين)
# ---------------------------------------------------------------------------
TEST_SUITE_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = TEST_SUITE_DIR / "test_db_invoices.sqlite3"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production-use-only"
os.environ["COOKIE_SECURE"] = "false"   # حتى تعمل الكوكيز بدون HTTPS في الاختبار (samesite=lax)
os.environ.pop("COOKIE_DOMAIN", None)
os.environ.pop("REDIS_URL", None)       # إجبار slowapi على وضع الذاكرة المحلية

BACKEND_DIR = TEST_SUITE_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# 2) استيراد app بعد ضبط متغيرات البيئة
# ---------------------------------------------------------------------------
from app.main import app
from app.database import Base, get_db
from app import models, schemas
from app.security import hash_password, CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.rate_limit import limiter
from app.assembly_crud import STAGE_COMPLETE

# نماذج الفوترة تستخدم نفس Base (raw import من app.database)، لذا
# Base.metadata.create_all تُنشئ جداول الفوترة تلقائيًا أيضًا دون أي خطوة إضافية
from invoicing import models as invoicing_models  # noqa: F401  (لضمان تسجيل الجداول في Base.metadata)

# ---------------------------------------------------------------------------
# 3) محرك اختبار مستقل (SQLite + StaticPool لتفادي مشاكل تعدد الاتصالات)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# ---------------------------------------------------------------------------
# 4) تعطيل Rate Limiting أثناء الاختبار
# ---------------------------------------------------------------------------
limiter.enabled = False


# ---------------------------------------------------------------------------
# 4.5) 🛡️ عميل اختبار "واعٍ" بحماية CSRF (نفس منطق conftest.py العام تمامًا)
# ---------------------------------------------------------------------------
class CSRFAwareTestClient(TestClient):
    def request(self, method, url, headers=None, **kwargs):
        headers = dict(headers or {})
        if method.upper() not in ("GET", "HEAD", "OPTIONS"):
            csrf_value = self.cookies.get(CSRF_COOKIE_NAME)
            if csrf_value:
                headers.setdefault(CSRF_HEADER_NAME, csrf_value)
        return super().request(method, url, headers=headers, **kwargs)


# ---------------------------------------------------------------------------
# 5) Fixtures عامة لدورة حياة القاعدة
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    with CSRFAwareTestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 6) زرع الأدوار الأساسية (admin / supervisor / operator)
# ---------------------------------------------------------------------------
@pytest.fixture
def seed_roles(db_session):
    roles_data = [
        dict(name=models.RoleNames.ADMIN, label="مدير", is_system=True,
             allowed_tabs=list(schemas.ALL_TAB_IDS)),
        dict(name=models.RoleNames.SUPERVISOR, label="مشرف", is_system=True,
             allowed_tabs=["assembly", "faults", "invoices", "customers", "workers", "users"]),
        dict(name=models.RoleNames.OPERATOR, label="عامل", is_system=True,
             allowed_tabs=["assembly", "faults"]),
    ]
    created = {}
    for data in roles_data:
        role = models.Role(**data)
        db_session.add(role)
        db_session.flush()
        created[data["name"]] = role
    db_session.commit()
    for key in created:
        db_session.refresh(created[key])
    return created


# 🆕 دور "فوترة فقط" (invoices فقط، بلا customers/faults/assembly/chassis) —
# يُستخدم لاختبار إصلاح صلاحيات القراءة العابرة للتبويبات (customers/faults/
# chassis) الذي أُجري لصالح مستخدمي الفوترة فقط.
@pytest.fixture
def seed_invoices_only_role(db_session):
    role = models.Role(
        name="invoices_only_role",
        label="فوترة فقط",
        is_system=False,
        allowed_tabs=["invoices"],
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


# 🆕 دور "عملاء فقط" — للتأكد (كضابط سلبي/negative control) أن من يملك
# customers فقط (بلا invoices وبلا faults) يبقى محجوبًا عن /api/faults/
@pytest.fixture
def seed_customers_only_role(db_session):
    role = models.Role(
        name="customers_only_role",
        label="عملاء فقط",
        is_system=False,
        allowed_tabs=["customers"],
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


# ---------------------------------------------------------------------------
# 7) مستخدمون جاهزون + تسجيل دخول
# ---------------------------------------------------------------------------
def _make_user(db_session, username, password, role, is_active=True, is_deleted=False):
    user = models.User(
        username=username,
        hashed_password=hash_password(password),
        full_name=username,
        role_id=role.id,
        is_active=is_active,
        is_deleted=is_deleted,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, seed_roles):
    return _make_user(db_session, "test_admin", "AdminPass123!", seed_roles[models.RoleNames.ADMIN])


@pytest.fixture
def supervisor_user(db_session, seed_roles):
    return _make_user(db_session, "test_supervisor", "SupervisorPass123!", seed_roles[models.RoleNames.SUPERVISOR])


@pytest.fixture
def operator_user(db_session, seed_roles):
    return _make_user(db_session, "test_operator", "OperatorPass123!", seed_roles[models.RoleNames.OPERATOR])


@pytest.fixture
def invoices_only_user(db_session, seed_invoices_only_role):
    return _make_user(db_session, "test_invoices_only", "InvoicesOnly123!", seed_invoices_only_role)


@pytest.fixture
def customers_only_user(db_session, seed_customers_only_role):
    return _make_user(db_session, "test_customers_only", "CustomersOnly123!", seed_customers_only_role)


def _login(client, username, password):
    response = client.post("/api/auth/login/", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response


@pytest.fixture
def authenticated_client(client, admin_user):
    """client مسجّل دخول بحساب admin (الكوكيز محفوظة تلقائيًا داخل client)"""
    _login(client, "test_admin", "AdminPass123!")
    return client


@pytest.fixture
def supervisor_client(client, supervisor_user):
    _login(client, "test_supervisor", "SupervisorPass123!")
    return client


@pytest.fixture
def operator_client(client, operator_user):
    _login(client, "test_operator", "OperatorPass123!")
    return client


@pytest.fixture
def invoices_only_client(client, invoices_only_user):
    _login(client, "test_invoices_only", "InvoicesOnly123!")
    return client


@pytest.fixture
def customers_only_client(client, customers_only_user):
    _login(client, "test_customers_only", "CustomersOnly123!")
    return client


# ---------------------------------------------------------------------------
# 8) مساعدات خاصة بالفوترة: عملاء + هياكل جاهزة للبيع
# ---------------------------------------------------------------------------
@pytest.fixture
def customer(db_session):
    """عميل واحد جاهز للاستخدام المباشر في اختبارات الفوترة"""
    c = models.Customer(name="عميل اختبار الفوترة")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def customer_factory(db_session):
    """مصنع عملاء لإنشاء أكثر من عميل بأسماء فريدة داخل نفس الاختبار"""
    counter = {"n": 0}

    def _make(name: str | None = None):
        counter["n"] += 1
        c = models.Customer(name=name or f"عميل اختبار رقم {counter['n']}")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    return _make


# 🛡️🆕 إصلاح جوهري: make_chassis لم يعد يعتمد على فِكستشر authenticated_client
# المشترك (الذي يستخدم كائن `client` نفسه المستخدم من قبل فِكستشرات أخرى
# كـ invoices_only_client أو customers_only_client). الاعتماد القديم كان
# يُسبب تصادم كوكيز صامت: أي اختبار يستخدم معًا (مثلاً) invoices_only_client
# و make_chassis كان فعليًا يُسجّل دخول admin *فوق* كوكيز invoices_only على
# نفس كائن client، فتنقلب كل الطلبات اللاحقة عبر invoices_only_client إلى
# طلبات بصلاحية admin بالخطأ (نفس الفخ الموثّق أصلاً في تعليق
# test_unauthenticated_cannot_create_fault، لكنه لم يكن معالَجًا هنا).
#
# الحل: استخدام TestClient معزول تمامًا (عميل خاص بعملية إنشاء الهيكل فقط،
# بكوكيز خاصة به) لتسجيل دخول admin وإنشاء سجل التجميع، دون أي تأثير على
# كوكيز أي فِكستشر client آخر مستخدم في نفس الاختبار.
@pytest.fixture
def make_chassis(admin_user):
    """
    🆕 مصنع هياكل "متاحة للبيع": يُسجِّل مرحلة (تجميع_كامل) دفعة واحدة عبر
    حساب admin على عميل TestClient معزول تمامًا (لا يشارك الكوكيز مع أي
    فِكستشر client آخر يُستخدم في نفس الاختبار)، فينتج هيكل مكتمل التجميع،
    بلا أعطال معلّقة، وغير مُباع بعد — أي جاهز تمامًا لإنشاء فاتورة عليه.
    """
    counter = {"n": 0}

    def _make(bike_type_name="نوع فحص الفوترة", bike_color_name="أحمر فحص", worker_name="عامل فحص الفوترة"):
        counter["n"] += 1
        chassis_number = f"INV-TEST-CHASSIS-{counter['n']:04d}"

        with CSRFAwareTestClient(app) as isolated_admin_client:
            _login(isolated_admin_client, "test_admin", "AdminPass123!")
            response = isolated_admin_client.post(
                "/api/assembly/record/?force=false",
                json={
                    "chassis_number": chassis_number,
                    "worker_name": worker_name,
                    "stage": STAGE_COMPLETE,
                    "bike_type_name": bike_type_name,
                    "bike_color_name": bike_color_name,
                },
            )
            assert response.status_code == 200, response.text

        return chassis_number

    return _make