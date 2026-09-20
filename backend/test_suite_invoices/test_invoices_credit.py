"""
test_invoices_credit.py - رصيد العميل (المحفظة الداخلية): الإيداع، التعديل اليدوي،
الاسترجاع النقدي، تسديد فاتورة من الرصيد، واستخدامه عند إنشاء الفاتورة/الدفع.
"""


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00"):
    return {"chassis_number": chassis_number, "unit_price": unit_price}


def _base(customer_id):
    return f"/api/invoices/customers/{customer_id}/credit"


def _balance(client, customer_id):
    return client.get(f"{_base(customer_id)}/").json()["credit_balance"]


def _ledger(client, customer_id):
    return client.get(f"{_base(customer_id)}/ledger/").json()


def _deposit(client, customer_id, amount, notes=None):
    return client.post(f"{_base(customer_id)}/deposit/", json={"amount": amount, "notes": notes})


# ====================== إيداع وتعديل ======================

def test_new_customer_credit_balance_is_zero(authenticated_client, customer):
    assert _balance(authenticated_client, customer.id) == "0.00"
    assert _ledger(authenticated_client, customer.id) == []


def test_deposit_increases_balance_and_records_ledger(authenticated_client, customer):
    response = _deposit(authenticated_client, customer.id, "400.00", "إيداع نقدي")
    assert response.status_code == 200, response.text
    assert response.json()["credit_balance"] == "400.00"

    _deposit(authenticated_client, customer.id, "100.00")
    assert _balance(authenticated_client, customer.id) == "500.00"

    ledger = _ledger(authenticated_client, customer.id)
    assert len(ledger) == 2
    assert {e["action_type"] for e in ledger} == {"deposit"}
    # الأحدث أولًا، و balance_after يعكس الرصيد بعد كل حركة
    assert ledger[0]["balance_after"] == "500.00"
    assert ledger[1]["balance_after"] == "400.00"
    assert ledger[1]["created_by_username"] == "test_admin"


def test_deposit_non_positive_amount_rejected(authenticated_client, customer):
    assert _deposit(authenticated_client, customer.id, "0").status_code == 422
    assert _deposit(authenticated_client, customer.id, "-5.00").status_code == 422


def test_deposit_unknown_customer_not_found(authenticated_client):
    assert _deposit(authenticated_client, 999999, "10.00").status_code == 404


def test_adjust_sets_new_balance_with_signed_ledger_entry(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "400.00")

    response = authenticated_client.post(
        f"{_base(customer.id)}/adjust/", json={"new_balance": "150.00", "notes": "تصحيح خطأ إدخال"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["credit_balance"] == "150.00"

    latest = _ledger(authenticated_client, customer.id)[0]
    assert latest["action_type"] == "manual_adjust"
    assert latest["amount"] == "-250.00"
    assert latest["balance_after"] == "150.00"


def test_adjust_same_or_negative_balance_rejected(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "100.00")

    same = authenticated_client.post(
        f"{_base(customer.id)}/adjust/", json={"new_balance": "100.00", "notes": "لا تغيير"}
    )
    assert same.status_code == 422

    negative = authenticated_client.post(
        f"{_base(customer.id)}/adjust/", json={"new_balance": "-1.00", "notes": "سالب"}
    )
    assert negative.status_code == 422


# ====================== استرجاع نقدي ======================

def test_cash_refund_partial_reduces_balance_and_appears_in_refund_log(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "500.00")

    response = authenticated_client.post(f"{_base(customer.id)}/refund/", json={"amount": "200.00"})
    assert response.status_code == 200, response.text
    assert response.json()["credit_balance"] == "300.00"

    log = authenticated_client.get("/api/invoices/credit-refunds/").json()
    assert log["total"] == 1
    assert log["items"][0]["customer_name"] == customer.name
    assert log["items"][0]["amount"] == "200.00"  # موجب في السجل رغم أن الحركة سالبة

    assert _ledger(authenticated_client, customer.id)[0]["action_type"] == "refunded"


def test_cash_refund_exceeding_balance_or_non_positive_rejected(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "100.00")

    too_much = authenticated_client.post(f"{_base(customer.id)}/refund/", json={"amount": "150.00"})
    assert too_much.status_code == 422

    zero = authenticated_client.post(f"{_base(customer.id)}/refund/", json={"amount": "0"})
    assert zero.status_code == 422

    assert _balance(authenticated_client, customer.id) == "100.00"
    assert authenticated_client.get("/api/invoices/credit-refunds/").json()["total"] == 0


def test_refund_log_ignores_non_refund_actions(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "100.00")
    assert authenticated_client.get("/api/invoices/credit-refunds/").json()["total"] == 0


# ====================== تسديد فاتورة من الرصيد ======================

def test_reallocate_pays_target_invoice_from_credit(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = invoice.json()["id"]
    _deposit(authenticated_client, customer.id, "400.00")

    response = authenticated_client.post(
        f"{_base(customer.id)}/reallocate/",
        json={"target_invoice_id": invoice_id, "amount": "300.00"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["credit_balance"] == "100.00"
    assert response.json()["target_invoice_number"] == invoice.json()["invoice_number"]

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["paid_amount"] == "300.00"
    assert detail["status"] == "partially_paid"
    assert detail["payments"][0]["payment_method"] == "من رصيد العميل"

    assert _ledger(authenticated_client, customer.id)[0]["action_type"] == "used_on_invoice"


def test_reallocate_full_remaining_marks_invoice_paid(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = invoice.json()["id"]
    _deposit(authenticated_client, customer.id, "1000.00")

    response = authenticated_client.post(
        f"{_base(customer.id)}/reallocate/",
        json={"target_invoice_id": invoice_id, "amount": "1000.00"},
    )
    assert response.status_code == 200
    assert _balance(authenticated_client, customer.id) == "0.00"
    assert authenticated_client.get(f"/api/invoices/{invoice_id}/").json()["status"] == "paid"


def test_reallocate_to_other_customers_invoice_rejected(authenticated_client, customer_factory, make_chassis):
    cust1, cust2 = customer_factory(), customer_factory()
    chassis = make_chassis()
    invoice_of_cust2 = _create_invoice(authenticated_client, cust2.id, [_item(chassis, "1000.00")])
    _deposit(authenticated_client, cust1.id, "500.00")

    response = authenticated_client.post(
        f"{_base(cust1.id)}/reallocate/",
        json={"target_invoice_id": invoice_of_cust2.json()["id"], "amount": "100.00"},
    )
    assert response.status_code == 400


def test_reallocate_exceeding_target_remaining_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "100.00")],
        initial_payment_amount="50.00",
    )
    _deposit(authenticated_client, customer.id, "900.00")

    response = authenticated_client.post(
        f"{_base(customer.id)}/reallocate/",
        json={"target_invoice_id": invoice.json()["id"], "amount": "900.00"},  # المتبقي 50 فقط
    )
    assert response.status_code == 422


def test_reallocate_exceeding_balance_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    _deposit(authenticated_client, customer.id, "100.00")

    response = authenticated_client.post(
        f"{_base(customer.id)}/reallocate/",
        json={"target_invoice_id": invoice.json()["id"], "amount": "500.00"},
    )
    assert response.status_code == 422


def test_reallocate_to_paid_or_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    paid = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "100.00")], initial_payment_amount="100.00"
    )
    cancelled = _create_invoice(authenticated_client, customer.id, [_item(c2, "100.00")])
    authenticated_client.post(
        f"/api/invoices/{cancelled.json()['id']}/cancel/", json={"confirm_no_reason": True}
    )
    _deposit(authenticated_client, customer.id, "500.00")

    for target in (paid, cancelled):
        response = authenticated_client.post(
            f"{_base(customer.id)}/reallocate/",
            json={"target_invoice_id": target.json()["id"], "amount": "10.00"},
        )
        assert response.status_code == 400


# ====================== استخدام الرصيد عند الإنشاء / الدفع ======================

def test_create_invoice_using_credit_as_partial_payment(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    _deposit(authenticated_client, customer.id, "500.00")

    response = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        use_credit_amount="300.00",
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "300.00"
    assert data["remaining_amount"] == "700.00"
    assert data["status"] == "partially_paid"
    assert data["payments"][0]["payment_method"] == "من رصيد العميل"

    assert _balance(authenticated_client, customer.id) == "200.00"
    assert _ledger(authenticated_client, customer.id)[0]["action_type"] == "used_on_invoice"


def test_create_invoice_credit_usage_capped_by_available_balance(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    _deposit(authenticated_client, customer.id, "100.00")

    response = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        use_credit_amount="900.00",
    )
    assert response.status_code == 200, response.text
    assert response.json()["paid_amount"] == "100.00"
    assert _balance(authenticated_client, customer.id) == "0.00"


def test_add_payment_mixing_cash_and_credit(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = invoice.json()["id"]
    _deposit(authenticated_client, customer.id, "250.00")

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "400.00", "payment_method": "cash", "use_credit_amount": "250.00"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "650.00"
    assert data["remaining_amount"] == "350.00"
    assert len(data["payments"]) == 2
    assert _balance(authenticated_client, customer.id) == "0.00"


def test_add_payment_with_only_credit(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    invoice = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = invoice.json()["id"]
    _deposit(authenticated_client, customer.id, "1000.00")

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "0", "use_credit_amount": "1000.00"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"
    assert _balance(authenticated_client, customer.id) == "0.00"


# ====================== قوائم وإحصائيات الرصيد ======================

def test_customers_with_credit_lists_only_positive_balances(authenticated_client, customer_factory):
    with_credit, without_credit = customer_factory(), customer_factory()
    _deposit(authenticated_client, with_credit.id, "75.00")

    response = authenticated_client.get("/api/invoices/customers-with-credit/")
    assert response.status_code == 200
    ids = {c["customer_id"] for c in response.json()}
    assert with_credit.id in ids
    assert without_credit.id not in ids


def test_invoice_stats_reflect_credit_and_refunds(authenticated_client, customer):
    _deposit(authenticated_client, customer.id, "500.00")
    authenticated_client.post(f"{_base(customer.id)}/refund/", json={"amount": "200.00"})

    stats = authenticated_client.get("/api/invoices/stats/summary/").json()
    assert stats["total_credit_balance"] == "300.00"
    assert stats["total_refunded"] == "200.00"
    # الإجمالي الشامل = صافي المحصَّل + المسترجَع + الأرصدة
    assert stats["total_gross_collected"] == "500.00"


def test_operator_without_invoices_tab_cannot_touch_credit(operator_client, customer):
    response = operator_client.post(
        f"{_base(customer.id)}/deposit/", json={"amount": "10.00"}
    )
    assert response.status_code == 403
