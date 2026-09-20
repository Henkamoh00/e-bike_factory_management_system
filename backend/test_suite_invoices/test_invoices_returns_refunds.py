"""
test_invoices_returns_refunds.py - إرجاع الدراجات المباعة، إلغاء الفواتير، سجل المرتجعات،
وكشف حساب العميل. (الفوائض الناتجة عن الإرجاع/الإلغاء تُحوَّل تلقائيًا إلى رصيد العميل —
اختبارات الرصيد نفسه في test_invoices_credit.py.)
"""
REASON_BROKEN = "الدراجة مكسورة"
REASON_CHASSIS_FAULT = "عطل في الهيكل"
REASON_OTHER = "سبب آخر"


def _create_invoice(client, customer_id, items, **extra):
    payload = {"customer_id": customer_id, "items": items}
    payload.update(extra)
    return client.post("/api/invoices/", json=payload)


def _item(chassis_number, unit_price="1000.00"):
    return {"chassis_number": chassis_number, "unit_price": unit_price}


def _credit(client, customer_id):
    return client.get(f"/api/invoices/customers/{customer_id}/credit/").json()["credit_balance"]


def _ledger(client, customer_id):
    return client.get(f"/api/invoices/customers/{customer_id}/credit/ledger/").json()


# ====================== إرجاع الدراجات المباعة ======================

def test_create_return_success_updates_totals(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item1_id, "reason": REASON_BROKEN},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chassis_number"] == c1
    assert data["invoice_number"] == created.json()["invoice_number"]
    assert data["reason"] == REASON_BROKEN
    assert data["created_by_username"] == "test_admin"

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    # المجموع الفرعي يبقى شاملًا كل البنود؛ البند المُرجَع يُخصم من الإجمالي فقط
    assert detail["subtotal"] == "1500.00"
    assert detail["total_amount"] == "500.00"
    returned_item = next(i for i in detail["items"] if i["id"] == item1_id)
    assert returned_item["is_returned"] is True
    assert returned_item["return_reason"] == REASON_BROKEN


def test_create_return_free_text_reason_rejected(authenticated_client, customer, make_chassis):
    """reason مقيَّد بـ Enum من 5 قيم ثابتة: أي نص حر يُرفض بـ 422."""
    chassis = make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(chassis)])
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item_id, "reason": "عطل في الشاحن"},
    )
    assert response.status_code == 422


def test_create_return_other_reason_keeps_free_text_in_notes(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    invoice_id = created.json()["id"]
    item_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/",
        json={"invoice_item_id": item_id, "reason": REASON_OTHER, "notes": "العميل غيّر رأيه"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["reason"] == REASON_OTHER
    assert response.json()["notes"] == "العميل غيّر رأيه"

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    returned_item = next(i for i in detail["items"] if i["id"] == item_id)
    assert returned_item["return_reason"] == REASON_OTHER
    assert returned_item["return_notes"] == "العميل غيّر رأيه"


def test_create_return_already_returned_rejected(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")])
    item1_id = created.json()["items"][0]["id"]

    first = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_BROKEN}
    )
    assert first.status_code == 200

    second = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_OTHER}
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
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": REASON_BROKEN}
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
        json={"invoice_item_id": item_id, "reason": REASON_CHASSIS_FAULT, "related_fault_id": fault_id},
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
        json={"invoice_item_id": item_id, "reason": REASON_CHASSIS_FAULT, "related_fault_id": fault_id},
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
            "reason": REASON_CHASSIS_FAULT,
            "create_fault_stage": "تجميع_الهيكل",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["related_fault_id"] is not None

    faults = authenticated_client.get("/api/faults/", params={"chassis_number": chassis}).json()
    assert faults["total"] == 1
    assert faults["items"][0]["status"] == "pending"
    assert faults["items"][0]["related_stage"] == "تجميع_الهيكل"


def test_return_with_surplus_payment_moves_difference_to_credit(authenticated_client, customer, make_chassis):
    """فاتورة مدفوعة بالكامل ثم إرجاع أحد بندَيها: الفرق يتحول لرصيد العميل والفاتورة تبقى مدفوعة."""
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")],
        initial_payment_amount="1500.00",
    )
    assert created.json()["status"] == "paid"
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]

    response = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_BROKEN}
    )
    assert response.status_code == 200, response.text

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["total_amount"] == "500.00"
    assert detail["paid_amount"] == "500.00"
    assert detail["remaining_amount"] == "0.00"
    assert detail["status"] == "paid"

    assert _credit(authenticated_client, customer.id) == "1000.00"
    ledger = _ledger(authenticated_client, customer.id)
    assert [e["action_type"] for e in ledger] == ["from_return"]
    assert ledger[0]["amount"] == "1000.00"
    assert ledger[0]["related_invoice_number"] == created.json()["invoice_number"]


def test_return_all_items_auto_cancels_invoice_and_moves_paid_to_credit(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(c1, "1000.00"), _item(c2, "500.00")],
        initial_payment_amount="600.00",
    )
    invoice_id = created.json()["id"]
    item1_id = created.json()["items"][0]["id"]
    item2_id = created.json()["items"][1]["id"]

    r1 = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_BROKEN}
    )
    assert r1.status_code == 200
    r2 = authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item2_id, "reason": REASON_BROKEN}
    )
    assert r2.status_code == 200

    detail = authenticated_client.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["status"] == "cancelled"
    assert detail["cancel_reason"] is not None

    # كل المبلغ المدفوع (600) انتقل لرصيد العميل عبر الإرجاعين
    assert _credit(authenticated_client, customer.id) == "600.00"
    assert {e["action_type"] for e in _ledger(authenticated_client, customer.id)} == {"from_return"}


def test_returnable_chassis_excludes_returned_and_cancelled(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    item1_id = created.json()["items"][0]["id"]

    authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_BROKEN}
    )

    returnable = authenticated_client.get("/api/invoices/returns/returnable-chassis/").json()
    chassis_numbers = {r["chassis_number"] for r in returnable}
    assert c1 not in chassis_numbers
    assert c2 in chassis_numbers


def test_returns_log_lists_created_returns(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, customer.id, [_item(c1), _item(c2)])
    item1_id = created.json()["items"][0]["id"]
    authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item1_id, "reason": REASON_BROKEN}
    )

    response = authenticated_client.get("/api/invoices/returns/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["chassis_number"] == c1
    assert data["items"][0]["customer_name"] == customer.name


def test_returned_chassis_can_be_sold_again(authenticated_client, customer_factory, make_chassis):
    cust1, cust2 = customer_factory(), customer_factory()
    chassis, other = make_chassis(), make_chassis()
    created = _create_invoice(authenticated_client, cust1.id, [_item(chassis), _item(other)])
    item_id = created.json()["items"][0]["id"]

    authenticated_client.post(
        "/api/invoices/returns/", json={"invoice_item_id": item_id, "reason": REASON_BROKEN}
    )

    resold = _create_invoice(authenticated_client, cust2.id, [_item(chassis)])
    assert resold.status_code == 200, resold.text


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


def test_cancel_invoice_with_payment_moves_paid_to_credit(authenticated_client, customer, make_chassis):
    chassis = make_chassis()
    created = _create_invoice(
        authenticated_client, customer.id, [_item(chassis, "1000.00")],
        initial_payment_amount="300.00",
    )
    invoice_id = created.json()["id"]

    response = authenticated_client.post(
        f"/api/invoices/{invoice_id}/cancel/",
        json={"reason": "طلب العميل", "confirm_refund": True},
    )
    assert response.status_code == 200

    assert _credit(authenticated_client, customer.id) == "300.00"
    ledger = _ledger(authenticated_client, customer.id)
    assert [e["action_type"] for e in ledger] == ["from_cancel"]
    assert ledger[0]["related_invoice_number"] == created.json()["invoice_number"]


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
    assert data["credit_balance"] == "0.00"
    assert data["credit_ledger"] == []
    assert len(data["invoices"]) == 2


def test_customer_statement_includes_credit_balance_and_ledger(authenticated_client, customer):
    authenticated_client.post(
        f"/api/invoices/customers/{customer.id}/credit/deposit/",
        json={"amount": "250.00", "notes": "إيداع تجريبي"},
    )

    data = authenticated_client.get(f"/api/invoices/customers/{customer.id}/statement/").json()
    assert data["credit_balance"] == "250.00"
    assert len(data["credit_ledger"]) == 1
    assert data["credit_ledger"][0]["action_type"] == "deposit"


def test_customer_statement_excludes_cancelled_invoices(authenticated_client, customer, make_chassis):
    c1, c2 = make_chassis(), make_chassis()
    keep = _create_invoice(authenticated_client, customer.id, [_item(c1, "1000.00")])
    dropped = _create_invoice(authenticated_client, customer.id, [_item(c2, "500.00")])
    authenticated_client.post(
        f"/api/invoices/{dropped.json()['id']}/cancel/", json={"confirm_no_reason": True}
    )

    data = authenticated_client.get(f"/api/invoices/customers/{customer.id}/statement/").json()
    assert [i["id"] for i in data["invoices"]] == [keep.json()["id"]]
    assert data["total_invoiced"] == "1000.00"


def test_customer_statement_customer_not_found(authenticated_client):
    response = authenticated_client.get("/api/invoices/customers/999999/statement/")
    assert response.status_code == 404
