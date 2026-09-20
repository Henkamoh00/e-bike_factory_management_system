"""
test_auth.py - تسجيل الدخول / الخروج / تجديد التوكن (rotation) / rate limiting
"""
from app.security import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME


def test_login_success(client, admin_user):
    response = client.post(
        "/api/auth/login/",
        json={"username": "test_admin", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    assert ACCESS_COOKIE_NAME in response.cookies
    assert REFRESH_COOKIE_NAME in response.cookies


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/auth/login/",
        json={"username": "test_admin", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client, seed_roles):
    response = client.post(
        "/api/auth/login/",
        json={"username": "no_such_user", "password": "whatever"},
    )
    assert response.status_code == 401


def test_login_inactive_user_rejected(client, db_session, seed_roles):
    from app import models
    from app.security import hash_password

    user = models.User(
        username="disabled_user",
        hashed_password=hash_password("Pass123!"),
        role_id=seed_roles[models.RoleNames.OPERATOR].id,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login/",
        json={"username": "disabled_user", "password": "Pass123!"},
    )
    assert response.status_code == 401


def test_me_endpoint_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_endpoint_with_valid_session(authenticated_client):
    response = authenticated_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "test_admin"


def test_refresh_token_rotation(authenticated_client):
    old_refresh = authenticated_client.cookies.get(REFRESH_COOKIE_NAME)

    response = authenticated_client.post("/api/auth/refresh/")
    assert response.status_code == 200

    new_refresh = authenticated_client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_refresh is not None
    assert new_refresh != old_refresh


def test_refresh_token_reuse_detected(authenticated_client):
    """
    إعادة استخدام refresh token بعد تدويره يجب أن تُرفض (كشف replay attack).

    ملاحظة تقنية: التلاعب بكوكيز نفس الـ TestClient بعد عدة طلبات متتالية
    غير موثوق (httpx قد يُخزّن نسخًا بنطاقات (domain) مختلفة ضمنيًا لنفس
    الاسم، مما يسبب CookieConflict عند القراءة). لتفادي هذا نهائيًا، نعزل
    الطلب الثاني (إعادة استخدام التوكن القديم) في TestClient جديد فارغ
    الكوكيز تمامًا، ونضع عليه القيمة القديمة فقط دون أي تعارض محتمل.

    🛡️🆕 ملاحظة CSRF: بما أن هذا العميل المعزول لا يمر بتسجيل دخول (لا يملك
    كوكي CSRF حقيقية صادرة عن السيرفر)، ولأن نمط Double Submit Cookie لا
    يتطلب أن تكون القيمة "حقيقية" بل فقط أن تتطابق الكوكي مع الهيدر، نضبط
    كوكي CSRF وهمية ونُرسل نفس القيمة كهيدر يدويًا — هذا يحاكي بالضبط ما
    يفعله متصفح حقيقي (JS يقرأ الكوكي ويرسلها بالهيدر)، ويسمح للطلب بالمرور
    من الميدل وير والوصول فعليًا لمنطق كشف إعادة الاستخدام في auth_crud.py.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    old_refresh = authenticated_client.cookies.get(REFRESH_COOKIE_NAME)
    assert old_refresh is not None

    first = authenticated_client.post("/api/auth/refresh/")
    assert first.status_code == 200

    rotated_refresh = authenticated_client.cookies.get(REFRESH_COOKIE_NAME)
    assert rotated_refresh != old_refresh

    # عميل معزول تمامًا، لا يشارك أي حالة كوكيز مع authenticated_client
    with TestClient(app) as replay_client:
        replay_client.cookies.set(REFRESH_COOKIE_NAME, old_refresh)

        # 🛡️🆕 محاكاة يدوية لنمط Double Submit Cookie: كوكي + هيدر متطابقان
        fake_csrf = "test-csrf-value-for-replay-detection"
        replay_client.cookies.set(CSRF_COOKIE_NAME, fake_csrf)

        second = replay_client.post(
            "/api/auth/refresh/",
            headers={CSRF_HEADER_NAME: fake_csrf},
        )
        assert second.status_code == 401


def test_refresh_without_cookie_rejected(client):
    response = client.post("/api/auth/refresh/")
    assert response.status_code == 401


def test_logout_clears_session(authenticated_client):
    response = authenticated_client.post("/api/auth/logout/")
    assert response.status_code == 200

    protected = authenticated_client.get("/api/auth/me")
    assert protected.status_code == 401


def test_login_rate_limiting_disabled_in_tests(client, admin_user):
    """limiter.enabled = False في conftest.py، فمحاولات متكررة يجب ألا تُرجع 429."""
    for _ in range(8):
        response = client.post(
            "/api/auth/login/",
            json={"username": "test_admin", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
