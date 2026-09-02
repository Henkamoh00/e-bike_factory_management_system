"""
conftest.py - بيئة اختبار معزولة بالكامل عن قاعدة البيانات والإعدادات الحقيقية.
حذف مجلد test_suite/ بالكامل يزيل كل أثر للاختبارات دون أي تأثير على المشروع.
"""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) ضبط متغيرات البيئة الوهمية قبل أي استيراد لـ app (database.py و security.py
#    يرميان RuntimeError/ValueError لو DATABASE_URL أو JWT_SECRET_KEY غير موجودين)
# ---------------------------------------------------------------------------
TEST_SUITE_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = TEST_SUITE_DIR / "test_db.sqlite3"

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
from app.security import hash_password
from app.rate_limit import limiter

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
# 4) تعطيل Rate Limiting أثناء الاختبار (5/دقيقة على /login تكسر الاختبارات المتكررة)
# ---------------------------------------------------------------------------
limiter.enabled = False


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
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 6) زرع الأدوار الأساسية (admin / supervisor / operator)
#    ملاحظة: allowed_tabs لدور admin غير مهم فعليًا لأن get_current_user في
#    security.py يفرض ALL_TAB_IDS تلقائيًا لأي مستخدم role == "admin"،
#    لكننا نضبطها بالكامل هنا للواقعية.
# ---------------------------------------------------------------------------
@pytest.fixture
def seed_roles(db_session):
    roles_data = [
        dict(name=models.RoleNames.ADMIN, label="مدير", is_system=True,
             allowed_tabs=list(schemas.ALL_TAB_IDS)),
        dict(name=models.RoleNames.SUPERVISOR, label="مشرف", is_system=True,
             allowed_tabs=["assembly", "faults", "sales", "customers", "workers", "users"]),
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
