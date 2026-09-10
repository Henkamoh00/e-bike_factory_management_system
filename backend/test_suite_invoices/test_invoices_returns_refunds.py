"""
test_invoices_returns_refunds.py - إرجاع الدراجات المباعة، إلغاء الفواتير،
ومعالجة المبالغ المسترجعة (refund) الجزئية والكاملة.
"""


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00"):
    return {"chassis_number": chassis_number, "unit_price": unit_price}


# ====================== إرجاع الدراجات المباعة ======================

def test_create_return_success_updates_totals(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item1_id, "reason": "عطل في الشاحن"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chassis_number"] == c1
    assert data["invoice_number"] == created.json()["invoice_number"]
    # 🛡️✅ تم إصلاح الخلل: created_by_username الآن يُعبَّأ فعليًا من
    # ret.created_by (بدل إرساله None صراحةً كما كان سابقًا)
    assert data["created_by_username"] == "test_admin"

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["subtotal"] == "500.00"
    assert detail["total_amount"] == "500.00"
    returned_item = next(i for i in detail["items"] if i["id"] == item1_id)
    assert returned_item["is_returned"] is True
    assert returned_item["return_reason"] == "عطل في الشاحن"


def test_create_return_already_returned_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    item1_id = created.json()["items"][0]["id"]

    first = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": "سبب أول"}
    )
    assert first.status_code == 200

    second = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": "سبب ثانٍ"}
    )
    assert second.status_code == 400


def test_create_return_on_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    cancel = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True}
    )
    assert cancel.status_code == 200

    response = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": "أي سبب"}
    )
    assert response.status_code == 400


def test_create_return_with_related_fault_id(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    item_id = created.json()["items"][0]["id"]

    fault = authenticated_client.post(
        "/api/faults/", json={"chassis_number": chassis, "description": "عطل مكتشف بعد البيع"}
    )
    assert fault.status_code == 200
    fault_id = fault.json()["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item_id, "reason": "عطل مسجَّل مسبقاً", "related_fault_id": fault_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["related_fault_id"] == fault_id


def test_create_return_with_invalid_related_fault_id_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    item_id = created.json()["items"][0]["id"]

    fault = authenticated_client.post(
        "/api/faults/", json={"chassis_number": c2, "description": "عطل لهيكل آخر"}
    )
    fault_id = fault.json()["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item_id, "reason": "محاولة ربط خاطئة", "related_fault_id": fault_id},
    )
    assert response.status_code == 404


def test_create_return_with_create_fault_stage_auto_creates_fault(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={
            "invoice_item_id": item_id,
            "reason": "عطل اكتُشف عند الإرجاع",
            "create_fault_stage": "تجميع_كامل",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["related_fault_id"] is not None

    faults = authenticated_client.get("/api/faults/", params={"chassis_number": chassis}).json()
    assert faults["total"] == 1
    assert faults["items"][0]["status"] == "pending"


def test_return_all_items_auto_cancels_invoice_and_shows_in_pending_refunds(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")],
        initial_payment_amount="600.00",
    )
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]
    item2_id = created.json()["items"][1]["id"]

    r1 = authenticated_client.post("/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": "سبب"})
    assert r1.status_code == 200
    r2 = authenticated_client.post("/api/invoices/returns/", json={"invoice_item_id": item2_id, "reason": "سبب"})
    assert r2.status_code == 200

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["status"] == "cancelled"
    assert detail["cancel_reason"] is not None

    pending = authenticated_client.get("/api/invoices/pending-refunds/").json()
    matching = next((p for p in pending if p["invoice_id"] == invoice_id), None)
    assert matching is not None
    assert matching["remaining_unprocessed"] == "600.00"


def test_returnable_chassis_excludes_returned_and_cancelled(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    item1_id = created.json()["items"][0]["id"]

    authenticated_client.post("/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": "سبب"})

    returnable = authenticated_client.get("/api/invoices/returns/returnable-chassis/").json()
    chassis_numbers = {r["chassis_number"] for r in returnable}
    assert c1 not in chassis_numbers
    assert c2 in chassis_numbers


def test_sold_faulty_chassis_lists_pending_fault_on_active_sale(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    _create_invoice(authenticated_client, customer.id, [_item(chassis)])

    fault = authenticated_client.post(
        "/api/faults/", json={"chassis_number": chassis, "description": "عطل بعد البيع"}
    )
    assert fault.status_code == 200

    response = authenticated_client.get("/api/invoices/sold-faulty-chassis/")
    assert response.status_code == 200
    data = response.json()
    matching = next((d for d in data if d["chassis_number"] == chassis), None)
    assert matching is not None
    assert len(matching["faults"]) == 1


# ====================== إلغاء الفاتورة ======================

def test_cancel_invoice_requires_reason_or_confirm(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis)])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(f"/api/invoices/{invoice_id}/cancel/", json={})
    assert response.status_code == 400

    response2 = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True}
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "cancelled"


def test_cancel_invoice_with_payment_requires_confirm_refund(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="300.00",
    )
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"reason": "طلب العميل"}
    )
    assert response.status_code == 400

    response2 = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/",
        json={"reason": "طلب العميل", "confirm_refund": True},
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "cancelled"


def test_cancel_already_cancelled_invoice_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis)])
    invoice_id = created.json()["id"]

    first = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True}
    )
    assert first.status_code == 200

    second = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/", json={"confirm_no_reason": True}
    )
    assert second.status_code == 400


# ====================== معالجة الاسترجاعات المالية (refund) ======================

def test_mark_invoice_refunded_partial_then_full(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]

    cancel = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/",
        json={"confirm_no_reason": True, "confirm_refund": True},
    )
    assert cancel.status_code == 200

    # استرجاع جزئي أول (150 من أصل 400)
    partial = authenticated_client.post(
        f"/api/invoices/{invoice_id}/refund/mark-refunded/", json={"amount": "150.00"}
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["resolved"] is False
    assert partial.json()["remaining_unprocessed"] == "250.00"

    pending = authenticated_client.get("/api/invoices/pending-refunds/").json()
    assert any(p["invoice_id"] == invoice_id and p["remaining_unprocessed"] == "250.00" for p in pending)

    resolved = authenticated_client.get("/api/invoices/resolved-refunds/").json()
    matching_resolved = next(r for r in resolved if r["invoice_id"] == invoice_id)
    assert matching_resolved["fully_resolved"] is False
    assert len(matching_resolved["actions"]) == 1

    # استرجاع الباقي بالكامل (250 متبقية)
    final = authenticated_client.post(
        f"/api/invoices/{invoice_id}/refund/mark-refunded/", json={"amount": "250.00"}
    )
    assert final.status_code == 200
    assert final.json()["resolved"] is True
    assert final.json()["remaining_unprocessed"] == "0.00"

    pending_after = authenticated_client.get("/api/invoices/pending-refunds/").json()
    assert not any(p["invoice_id"] == invoice_id for p in pending_after)

    resolved_after = authenticated_client.get("/api/invoices/resolved-refunds/").json()
    matching_after = next(r for r in resolved_after if r["invoice_id"] == invoice_id)
    assert matching_after["fully_resolved"] is True
    assert len(matching_after["actions"]) == 2


def test_mark_invoice_refunded_exceeds_remaining_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice_id = created.json()["id"]
    authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/",
        json={"confirm_no_reason": True, "confirm_refund": True},
    )

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/refund/mark-refunded/", json={"amount": "500.00"}
    )
    assert response.status_code == 422


def test_mark_invoice_refunded_on_invoice_without_pool_rejected(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis, "1000.00")])
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/refund/mark-refunded/", json={"amount": "10.00"}
    )
    assert response.status_code == 400


def test_reallocate_invoice_refund_success(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    invoice1 = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice1_id = invoice1.json()["id"]
    authenticated_client.post(
        f"/api/invoices/{invoice1_id}/cancel/",
        json={"confirm_no_reason": True, "confirm_refund": True},
    )

    invoice2 = _create_invoice(authenticated_client, customer.id, [_item(c2, "1000.00")])
    invoice2_id = invoice2.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice1_id}/refund/reallocate/",
        json={"target_invoice_id": invoice2_id, "amount": "200.00"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["remaining_unprocessed"] == "200.00"

    target_detail = authenticated_client.get(f"/api/invoices/{invoice2_id}/").json()
    assert target_detail["paid_amount"] == "200.00"
    assert target_detail["status"] == "partially_paid"


def test_reallocate_invoice_refund_different_customer_rejected(authenticated_client, customer_factory, make_chassis):
    cust1 = customer_factory()
    cust2 = customer_factory()
    c1, c2 = make_chassis(), make_chassis()

    invoice1 = _create_invoice(
        authenticated_client, cust1.id, [_item(c1, "1000.00")],
        initial_payment_amount="400.00",
    )
    invoice1_id = invoice1.json()["id"]
    authenticated_client.post(
        f"/api/invoices/{invoice1_id}/cancel/",
        json={"confirm_no_reason": True, "confirm_refund": True},
    )

    invoice2 = _create_invoice(authenticated_client, cust2.id, [_item(c2, "1000.00")])
    invoice2_id = invoice2.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice1_id}/refund/reallocate/",
        json={"target_invoice_id": invoice2_id, "amount": "100.00"},
    )
    assert response.status_code == 400


def test_reallocate_invoice_refund_exceeds_target_remaining_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    invoice1 = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00")],
        initial_payment_amount="1000.00",
    )
    invoice1_id = invoice1.json()["id"]
    authenticated_client.post(
        f"/api/invoices/{invoice1_id}/cancel/",
        json={"confirm_no_reason": True, "confirm_refund": True},
    )

    invoice2 = _create_invoice(
        authenticated_client, customer.id, [_item(c2, "100.00")],
        initial_payment_amount="50.00",
    )
    invoice2_id = invoice2.json()["id"]  # المتبقي على الفاتورة الهدف = 50 فقط

    response = authenticated_client.post(
        f"/api/invoices/{invoice1_id}/refund/reallocate/",
        json={"target_invoice_id": invoice2_id, "amount": "900.00"},
    )
    assert response.status_code == 422


# ====================== كشف حساب العميل ======================

def test_customer_statement_totals(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00")],
        initial_payment_amount="400.00",
    )
    _create_invoice(
        authenticated_client, customer.id, [_item(c2, "500.00")],
        initial_payment_amount="500.00",
    )

    response = authenticated_client.get(f"/api/invoices/customers/{customer.id}/statement/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_invoiced"] == "1500.00"
    assert data["total_paid"] == "900.00"
    assert data["total_remaining"] == "600.00"
    assert len(data["invoices"]) == 2


def test_customer_statement_customer_not_found(authenticated_client):
    response = authenticated_client.get("/api/invoices/customers/999999/statement/")
    assert response.status_code == 404