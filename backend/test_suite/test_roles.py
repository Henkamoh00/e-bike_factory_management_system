"""
test_roles.py - إدارة الأدوار: الإنشاء، حماية صلاحيات admin، الحذف
"""
from app import schemas


def test_create_role(authenticated_client):
    response = authenticated_client.post(
        "/api/roles/",
        json={
            "name": "quality_inspector",
            "label": "مفتش جودة",
            "description": "دور تجريبي",
            "allowed_tabs": ["faults", "assembly"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "quality_inspector"
    assert data["allowed_tabs"] == ["faults", "assembly"]


def test_create_role_requires_admin(supervisor_client):
    response = supervisor_client.post(
        "/api/roles/",
        json={"name": "some_role", "label": "دور", "allowed_tabs": []},
    )
    assert response.status_code == 403


def test_admin_role_tabs_cannot_be_restricted(authenticated_client, seed_roles):
    """حتى لو حاول admin نفسه تقييد صلاحيات دور admin، يجب أن تبقى كاملة (كل التبويبات)."""
    admin_role_id = seed_roles["admin"].id
    response = authenticated_client.put(
        f"/api/roles/{admin_role_id}/",
        json={"allowed_tabs": ["invoices"]},
    )
    assert response.status_code == 200
    assert set(response.json()["allowed_tabs"]) == set(schemas.ALL_TAB_IDS)


def test_supervisor_cannot_grant_admin_role(supervisor_client, db_session, seed_roles):
    """المشرف (لديه صلاحية تبويب users) لا يمكنه إنشاء مستخدم بدور admin."""
    response = supervisor_client.post(
        "/api/users/",
        json={"username": "sneaky_admin", "password": "Pass12345!", "role": "admin"},
    )
    assert response.status_code == 403


def test_supervisor_cannot_grant_admin_role_via_update(supervisor_client, db_session, seed_roles):
    from app import models
    from app.security import hash_password

    target = models.User(
        username="promote_me",
        hashed_password=hash_password("Pass12345!"),
        role_id=seed_roles[models.RoleNames.OPERATOR].id,
        is_active=True,
    )
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    response = supervisor_client.put(
        f"/api/users/{target.id}/",
        json={"role": "admin"},
    )
    assert response.status_code == 403


def test_delete_role_in_use_rejected(authenticated_client, db_session, seed_roles):
    from app import models
    from app.security import hash_password

    user = models.User(
        username="uses_operator_role",
        hashed_password=hash_password("Pass123!"),
        role_id=seed_roles[models.RoleNames.OPERATOR].id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = authenticated_client.delete(f"/api/roles/{seed_roles['operator'].id}/")
    assert response.status_code == 400


def test_delete_system_role_rejected(authenticated_client, seed_roles):
    """أدوار النظام الأساسية (admin/supervisor/operator) لا يمكن حذفها حتى بلا مستخدمين."""
    response = authenticated_client.delete(f"/api/roles/{seed_roles['operator'].id}/")
    assert response.status_code == 400
    assert "نظام" in response.json()["detail"] or "حذف" in response.json()["detail"]


def test_delete_unused_non_system_role_succeeds(authenticated_client):
    create_resp = authenticated_client.post(
        "/api/roles/",
        json={"name": "temp_role", "label": "دور مؤقت", "allowed_tabs": []},
    )
    assert create_resp.status_code == 200
    role_id = create_resp.json()["id"]

    delete_resp = authenticated_client.delete(f"/api/roles/{role_id}/")
    assert delete_resp.status_code == 200