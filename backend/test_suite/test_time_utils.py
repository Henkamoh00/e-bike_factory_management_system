"""
اختبارات دوال الوقت الموحَّدة (app/time_utils.py) — لا تحتاج قاعدة بيانات.
تغطي تحديدًا الحافة التي ذكرها NOTES.md: انتهاء الصلاحية القريب من اللحظة الحالية،
والمقارنة بين قيم naive (SQLite) و aware (PostgreSQL) وبفروق توقيت مختلفة.
"""
from datetime import datetime, timedelta, timezone

from app.time_utils import (
    ensure_utc, format_local, is_expired, local_naive_to_utc, local_start_of_day_utc, to_local, utcnow,
)

NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_utcnow_is_aware_utc():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_ensure_utc_naive_is_treated_as_utc():
    naive = datetime(2026, 9, 19, 12, 0, 0)
    result = ensure_utc(naive)
    assert result == NOW
    assert result.tzinfo is not None


def test_ensure_utc_converts_other_offsets():
    plus_one = timezone(timedelta(hours=1))
    local = datetime(2026, 9, 19, 13, 0, 0, tzinfo=plus_one)
    assert ensure_utc(local) == NOW


def test_ensure_utc_none():
    assert ensure_utc(None) is None


def test_expired_one_second_ago():
    assert is_expired(NOW - timedelta(seconds=1), now=NOW) is True


def test_valid_one_second_ahead():
    assert is_expired(NOW + timedelta(seconds=1), now=NOW) is False


def test_exact_boundary_is_expired():
    assert is_expired(NOW, now=NOW) is True


def test_naive_and_aware_give_same_result():
    naive_future = (NOW + timedelta(minutes=5)).replace(tzinfo=None)
    aware_future = NOW + timedelta(minutes=5)
    assert is_expired(naive_future, now=NOW) == is_expired(aware_future, now=NOW) is False
    naive_past = (NOW - timedelta(minutes=5)).replace(tzinfo=None)
    aware_past = NOW - timedelta(minutes=5)
    assert is_expired(naive_past, now=NOW) == is_expired(aware_past, now=NOW) is True


def test_non_utc_offset_does_not_cause_false_expiry():
    # 13:30 بتوقيت +01:00 = 12:30 UTC → صالح عند 12:00 UTC
    plus_one = timezone(timedelta(hours=1))
    expires = datetime(2026, 9, 19, 13, 30, 0, tzinfo=plus_one)
    assert is_expired(expires, now=NOW) is False
    # 12:30 بتوقيت +01:00 = 11:30 UTC → منتهٍ عند 12:00 UTC
    expires2 = datetime(2026, 9, 19, 12, 30, 0, tzinfo=plus_one)
    assert is_expired(expires2, now=NOW) is True


# ====================== توقيت الجزائر (Africa/Algiers = UTC+1 ثابت) ======================

def test_local_start_of_day_is_previous_day_2300_utc():
    assert local_start_of_day_utc(2026, 9, 19) == datetime(2026, 9, 18, 23, 0, 0, tzinfo=timezone.utc)


def test_payment_just_after_local_midnight_belongs_to_new_local_day():
    # 23:30 UTC = 00:30 بتوقيت الجزائر من اليوم التالي → يُحسب ضمن "اليوم" 19 وليس 18
    since = local_start_of_day_utc(2026, 9, 19)
    payment = datetime(2026, 9, 18, 23, 30, 0, tzinfo=timezone.utc)
    assert ensure_utc(payment) >= since


def test_payment_just_before_local_midnight_belongs_to_previous_day():
    since = local_start_of_day_utc(2026, 9, 19)
    payment = datetime(2026, 9, 18, 22, 59, 59, tzinfo=timezone.utc)
    assert ensure_utc(payment) < since


def test_format_local_shifts_date_forward_after_2300_utc():
    assert format_local(datetime(2026, 9, 18, 23, 30, 0, tzinfo=timezone.utc)) == "2026-09-19"
    assert format_local(datetime(2026, 9, 18, 22, 30, 0)) == "2026-09-18"  # naive = UTC
    assert format_local(None) == ""


def test_to_local_offset_is_plus_one():
    local = to_local(datetime(2026, 9, 19, 12, 0, 0))
    assert local.utcoffset() == timedelta(hours=1)
    assert local.hour == 13


def test_local_naive_to_utc_interprets_naive_as_algiers():
    assert local_naive_to_utc(datetime(2026, 9, 19)) == datetime(2026, 9, 18, 23, 0, 0, tzinfo=timezone.utc)
    aware = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
    assert local_naive_to_utc(aware) == aware
