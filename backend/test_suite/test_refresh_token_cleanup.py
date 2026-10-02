"""
test_refresh_token_cleanup.py - تنظيف توكنات التحديث القديمة (auth_crud.purge_expired_refresh_tokens)
"""
from datetime import timedelta

from app import models, auth_crud
from app.time_utils import utcnow


def _add_token(db_session, user_id, suffix, expires_at, revoked=False):
    token = models.RefreshToken(
        token_hash=f"hash-{suffix}",
        user_id=user_id,
        expires_at=expires_at,
        revoked=revoked,
    )
    db_session.add(token)
    db_session.commit()
    return token


def _remaining_hashes(db_session):
    return {t.token_hash for t in db_session.query(models.RefreshToken).all()}


def test_purge_deletes_only_tokens_expired_over_30_days_ago(db_session, admin_user):
    now = utcnow()
    _add_token(db_session, admin_user.id, "old-revoked", now - timedelta(days=45), revoked=True)
    _add_token(db_session, admin_user.id, "old-unrevoked", now - timedelta(days=31))
    _add_token(db_session, admin_user.id, "recent-expired", now - timedelta(days=10), revoked=True)
    _add_token(db_session, admin_user.id, "still-valid", now + timedelta(days=5))

    deleted = auth_crud.purge_expired_refresh_tokens(db_session)

    assert deleted == 2
    assert _remaining_hashes(db_session) == {"hash-recent-expired", "hash-still-valid"}


def test_purge_with_nothing_to_delete_returns_zero(db_session, admin_user):
    _add_token(db_session, admin_user.id, "valid", utcnow() + timedelta(days=3))

    assert auth_crud.purge_expired_refresh_tokens(db_session) == 0
    assert _remaining_hashes(db_session) == {"hash-valid"}


def test_purge_does_not_break_active_session(authenticated_client, db_session):
    """التنظيف لا يمسّ جلسة المستخدم الحالية: التجديد والـ /me يعملان بعده."""
    auth_crud.purge_expired_refresh_tokens(db_session)

    assert authenticated_client.get("/api/auth/me").status_code == 200
    assert authenticated_client.post("/api/auth/refresh/").status_code == 200
