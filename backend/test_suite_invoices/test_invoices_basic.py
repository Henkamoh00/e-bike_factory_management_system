"""
test_invoices_basic.py - إنشاء الفاتورة، البنود، الدفعات، وحالات القفل (paid).
"""


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00", notes=None):
    d = {"chassis_number": chassis_number, "unit_price": unit_price}
    if notes is not None:
        d["notes"] = notes
    return d


# ====================== إنشاء الفاتورة ======================

def test_create_invoice_with_items_and_initial_payment(authenticated_client, customer, make_chassis):
    c1 = make_chassis()
    c2 = make_chassis()

    response = _create_invoice(
        authenticated_client,
        customer.id,
        [_item(c1, "1000.00"), _item(c2, "500.00")],
        initial_payment_amount="600.00",
        initial_payment_method="cash",
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["subtotal"] == "1500.00"
    assert data["total_amount"] == "1500.00"
    assert data["paid_amount"] == "600.00"
    assert data["remaining_amount"] == "900.00"
    assert data["status"] == "partially_paid"
    assert len(data["items"]) == 2
    assert len(data["payments"]) == 1
    assert data["customer_name"] == customer.name
    assert data["created_by_username"] == "test_admin"


def test_create_invoice_requires_at_least_one_item(authenticated_client, customer):
    response = _create_invoice(authenticated_client, customer.id, [])
    assert response.status_code == 422


def test_create_invoice_customer_not_found(authenticated_client, make_chassis):
    c1 = make_chassis()
    response = _create_invoice(authenticated_client, 999999, [_item(c1)])
    assert response.status_code == 404


def test_create_invoice_chassis_already_sold_conflict(authenticated_client, customer_factory, make_chassis):
    cust1 = customer_factory()
    cust2 = customer_factory()
    chassis = make_chassis()

    first = _create_invoice(authenticated_client, cust1.id, [_item(chassis)])
    assert first.status_code == 200

    second = _create_invoice(authenticated_client, cust2.id, [_item(chassis)])
    assert second.status_code == 409


def test_create_invoice_initial_payment_exceeds_total_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    response = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "500.00")],
        initial_payment_amount="600.00",
    )
    assert response.status_code == 422


def test_create_invoice_full_initial_payment_marks_paid(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    response = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="1000.00",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paid"
    assert data["remaining_amount"] == "0.00"


def test_unauthenticated_cannot_access_invoices(client):
    response = client.get("/api/invoices/")
    assert response.status_code == 401


def test_get_invoice_detail_not_found(authenticated_client):
    response = authenticated_client.get("/api/invoices/999999/")
    assert response.status_code == 404


# ====================== تعديل/حذف بند الفاتورة ======================

def test_update_invoice_item_price_success(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/items/{item_id}/",
        json={"unit_price": "1200.00"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["subtotal"] == "1200.00"
    assert data["total_amount"] == "1200.00"


def test_update_invoice_item_on_paid_invoice_locked(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="1000.00",
    )
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/items/{item_id}/",
        json={"unit_price": "1200.00"},
    )
    assert response.status_code == 400
    assert "مقفلة" in response.json()["detail"]


def test_delete_invoice_item_last_item_no_payments_hard_delete(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item_id}/")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # الفاتورة حُذفت فعليًا بالكامل
    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/")
    assert detail.status_code == 404


def test_delete_invoice_item_last_item_with_payments_requires_confirm(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    first_try = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item_id}/")
    assert first_try.status_code == 409
    assert first_try.headers.get("x-confirm-required") == "true"

    confirmed = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item_id}/?confirm=true")
    assert confirmed.status_code == 200
    data = confirmed.json()
    assert data["status"] == "cancelled"
    assert data["items"] == []


def test_delete_invoice_item_two_items_recomputes_totals(authenticated_client, customer, make_chassis):
    c1 = make_chassis()
    c2 = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item1_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["subtotal"] == "500.00"
    assert data["total_amount"] == "500.00"
    assert len(data["items"]) == 1


def test_delete_invoice_item_returned_item_rejected(authenticated_client, customer, make_chassis):
    c1 = make_chassis()
    c2 = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    ret = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item1_id, "reason": "عطل تصنيع"},
    )
    assert ret.status_code == 200, ret.text

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/items/{item1_id}/")
    assert response.status_code == 400
    assert "إرجاع" in response.json()["detail"]


def test_update_invoice_item_returned_item_rejected(authenticated_client, customer, make_chassis):
    c1 = make_chassis()
    c2 = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    ret = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item1_id, "reason": "عطل تصنيع"},
    )
    assert ret.status_code == 200, ret.text

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/items/{item1_id}/",
        json={"unit_price": "999.00"},
    )
    assert response.status_code == 400


# ====================== الدفعات ======================

def test_add_payment_success(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "400.00", "payment_method": "cash"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "400.00"
    assert data["remaining_amount"] == "600.00"
    assert data["status"] == "partially_paid"


def test_add_payment_exceeds_remaining_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "1500.00"},
    )
    assert response.status_code == 422


def test_add_payment_zero_or_negative_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "0"},
    )
    assert response.status_code == 422


def test_add_payment_on_paid_invoice_locked(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="1000.00",
    )
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "100.00"},
    )
    assert response.status_code == 400
    assert "مقفلة" in response.json()["detail"]


def test_add_payment_on_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]

    cancel = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/",
        json={"confirm_no_reason": True},
    )
    assert cancel.status_code == 200

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/payments/",
        json={"amount": "100.00"},
    )
    assert response.status_code == 400


def test_update_payment_success(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]
    payment_id = created.json()["payments"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/{payment_id}/",
        json={"amount": "700.00"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "700.00"
    assert data["remaining_amount"] == "300.00"


def test_update_payment_exceeds_total_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]
    payment_id = created.json()["payments"][0]["id"]

    response = authenticated_client.put(
        f"/api/invoices/{invoice_id}/payments/{payment_id}/",
        json={"amount": "1500.00"},
    )
    assert response.status_code == 422


def test_delete_payment_success_reverts_status(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]
    payment_id = created.json()["payments"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/payments/{payment_id}/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["paid_amount"] == "0.00"
    assert data["status"] == "confirmed"
    assert data["payments"] == []


def test_delete_payment_on_fully_paid_invoice_locked(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="1000.00",
    )
    invoice_id = created.json()["id"]
    payment_id = created.json()["payments"][0]["id"]

    response = authenticated_client.delete(f"/api/invoices/{invoice_id}/payments/{payment_id}/")
    assert response.status_code == 400
    assert "مقفلة" in response.json()["detail"]