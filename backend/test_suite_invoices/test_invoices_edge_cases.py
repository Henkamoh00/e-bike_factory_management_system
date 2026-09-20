"""
test_invoices_edge_cases.py - حالات حدّية لمنطق الفوترة المالي (خصومات، فوائض التعديل والحذف،
تحقّقات الدفعات) تحمي أي إعادة هيكلة مستقبلية لـ invoices_crud.py.
"""


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00"):
    return {"chassis_number": chassis_number, "unit_price": unit_price}


def _credit(client, customer_id):
    return client.get(f"/api/invoices/customers/{customer_id}/credit/").json()["credit_balance"]


def _ledger_types(client, customer_id):
    ledger = client.get(f"/api/invoices/customers/{customer_id}/credit/ledger/").json()
    return [e["action_type"] for e in ledger]


# ====================== الخصومات ======================

def test_percentage_discount_reduces_total(authenticated_client, customer, make_chassis):
    response = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        discount_type="percentage", discount_value="10",
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["subtotal"] == "1000.00"
    assert data["total_amount"] == "900.00"
    assert data["remaining_amount"] == "900.00"


def test_fixed_discount_reduces_total(authenticated_client, customer, make_chassis):
    response = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        discount_type="fixed", discount_value="250",
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_amount"] == "750.00"


def test_discount_larger_than_subtotal_floors_total_at_zero(authenticated_client, customer, make_chassis):
    response = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "100.00")],
        discount_type="fixed", discount_value="500",
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_amount"] == "0.00"


def test_negative_initial_payment_or_credit_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    assert _create_invoice(
        authenticated_client, customer.id, [_item(c1)], initial_payment_amount="-1"
    ).status_code == 422
    assert _create_invoice(
        authenticated_client, customer.id, [_item(c2)], use_credit_amount="-1"
    ).status_code == 422


# ====================== تعديل بند ======================

def test_update_item_notes_only_keeps_totals(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis(), "1000.00")])
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.put(f"/api/invoices/{invoice_id}/items/{item_id}/", json={"notes": "ملاحظة"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["items"][0]["notes"] == "ملاحظة"
    assert data["total_amount"] == "1000.00"


def test_update_item_without_any_field_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.put(f"/api/invoices/{invoice_id}/items/{item_id}/", json={})
    assert response.status_code == 422


def test_update_item_non_positive_price_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/items/{item_id}/", json={"unit_price": "0"}
    )
    assert response.status_code == 422


def test_update_item_unknown_item_not_found(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    response = authenticated_client.put(
        f"/api/invoices/{created.json()['id']}/items/999999/", json={"unit_price": "10"}
    )
    assert response.status_code == 404


def test_update_item_price_below_paid_moves_surplus_to_credit(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="600.00",
    )
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/items/{item_id}/", json={"unit_price": "400.00"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_amount"] == "400.00"
    assert data["paid_amount"] == "400.00"
    assert data["remaining_amount"] == "0.00"
    assert data["status"] == "paid"
    assert _credit(authenticated_client, customer.id) == "200.00"
    assert _ledger_types(authenticated_client, customer.id) == ["from_adjustment"]


# ====================== حذف بند ======================

def test_delete_non_last_item_with_surplus_moves_difference_to_credit(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00"), _item(make_chassis(), "500.00")],
        initial_payment_amount="700.00",
    )
    invoice_id = created.json()["id"]
    first_item_id = created.json()["items"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{first_item_id}/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_amount"] == "500.00"
    assert data["paid_amount"] == "500.00"
    assert data["status"] == "paid"
    assert _credit(authenticated_client, customer.id) == "200.00"
    assert _ledger_types(authenticated_client, customer.id) == ["from_adjustment"]


def test_delete_last_item_with_payments_confirmed_moves_paid_to_credit(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item_id}/?confirm=true")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert _credit(authenticated_client, customer.id) == "400.00"
    assert _ledger_types(authenticated_client, customer.id) == ["from_cancel"]


def test_delete_item_on_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]
    authenticated_client.post(f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True})

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item_id}/")
    assert response.status_code == 400


# ====================== الدفعات ======================

def test_add_payment_negative_cash_or_credit_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    invoice_id = created.json()["id"]

    assert authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/", json={"amount": "-5"}
    ).status_code == 422
    assert authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/", json={"amount": "10", "use_credit_amount": "-5"}
    ).status_code == 422


def test_add_payment_unknown_invoice_not_found(authenticated_client):
    response = authenticated_client.post("/api/invoices/999999/payments/", json={"amount": "10"})
    assert response.status_code == 404


def test_add_payment_records_custom_payment_date_and_method(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis())])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "100.00", "payment_method": "bank", "notes": "دفعة", "payment_date": "2026-01-15T10:00:00"},
    )
    assert response.status_code == 200, response.text
    payment = response.json()["payments"][0]
    assert payment["payment_method"] == "bank"
    assert payment["notes"] == "دفعة"
    assert payment["payment_date"].startswith("2026-01-15")


def test_update_payment_method_and_notes_only_keeps_amounts(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id, payment_id = created.json()["id"], created.json()["payments"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/{payment_id}/",
        json={"payment_method": "check", "notes": "تعديل"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "400.00"
    assert data["status"] == "partially_paid"
    assert data["payments"][0]["payment_method"] == "check"
    assert data["payments"][0]["notes"] == "تعديل"


def test_update_payment_to_full_amount_marks_paid(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id, payment_id = created.json()["id"], created.json()["payments"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/{payment_id}/", json={"amount": "1000.00"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"
    assert response.json()["remaining_amount"] == "0.00"


def test_update_payment_non_positive_or_unknown_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id, payment_id = created.json()["id"], created.json()["payments"][0]["id"]

    assert authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/{payment_id}/", json={"amount": "0"}
    ).status_code == 422
    assert authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/999999/", json={"amount": "10"}
    ).status_code == 404


def test_delete_payment_on_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id, payment_id = created.json()["id"], created.json()["payments"][0]["id"]
    authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True, "confirm_refund": True}
    )

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/payments/{payment_id}/")
    assert response.status_code == 400


# ====================== الإرجاع ======================

def test_return_partial_unpaid_keeps_invoice_confirmed(authenticated_client, customer, make_chassis):
    created = _create_invoice(
        authenticated_client, customer.id, [_item(make_chassis(), "1000.00"), _item(make_chassis(), "500.00")],
    )
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": "الدراجة مكسورة"}
    )
    assert response.status_code == 200, response.text
    detail = authenticated_client.get(f"/api/invoices/{created.json()['id']}/").json()
    assert detail["status"] == "confirmed"
    assert detail["total_amount"] == "500.00"
    assert detail["remaining_amount"] == "500.00"
    assert _credit(authenticated_client, customer.id) == "0.00"


def test_return_unknown_item_not_found(authenticated_client):
    response = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": 999999, "reason": "الدراجة مكسورة"}
    )
    assert response.status_code == 404


def test_return_all_items_unpaid_cancels_without_credit(authenticated_client, customer, make_chassis):
    created = _create_invoice(authenticated_client, customer.id, [_item(make_chassis(), "1000.00")])
    invoice_id, item_id = created.json()["id"], created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": "الدراجة مكسورة"}
    )
    assert response.status_code == 200, response.text
    assert authenticated_client.get(f"/api/invoices/{invoice_id}/").json()["status"] == "cancelled"
    assert _credit(authenticated_client, customer.id) == "0.00"
