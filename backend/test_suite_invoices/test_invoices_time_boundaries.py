"""
test_invoices_time_boundaries.py - حدود "اليوم" في إحصائيات الفواتير بتوقيت الجزائر
(Africa/Algiers) لا UTC — راجع app/time_utils.py و NOTES.md.
"""
from datetime import timedelta

from app.time_utils import local_start_of_day_utc, to_local, utcnow


def _today_start_utc():
    now_local = to_local(utcnow())
    return local_start_of_day_utc(now_local.year, now_local.month, now_local.day)


def test_today_revenue_uses_algiers_day_boundary(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = authenticated_client.post(
        "/api/invoices/",
        json={"customer_id": customer.id, "items": [{"chassis_number": chassis, "unit_price": "1000.00"}]},
    )
    assert created.status_code == 200, created.text
    invoice_id = created.json()["id"]

    today_start = _today_start_utc()

    # دفعة قبل منتصف الليل المحلي بدقيقة → "أمس" ولا تُحسب في اليوم
    before = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "100.00", "payment_date": (today_start - timedelta(minutes=1)).isoformat()},
    )
    assert before.status_code == 200, before.text

    # دفعة عند منتصف الليل المحلي تمامًا → تُحسب في اليوم
    at_start = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "200.00", "payment_date": today_start.isoformat()},
    )
    assert at_start.status_code == 200, at_start.text

    stats = authenticated_client.get("/api/invoices/stats/summary/").json()
    assert stats["today_revenue"] == "200.00"
    assert stats["total_collected"] == "300.00"
    assert stats["today_count"] == 1
