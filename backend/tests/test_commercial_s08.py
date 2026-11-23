from io import BytesIO
from pypdf import PdfReader
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.auth import router as auth_router
from app.api.invoices import router as invoices_router
from app.api.orders import router as orders_router
from app.database import Base, get_db
from app.models import Order, Product
from app.models_commercial import (
    CommercialInvoice,
    InvoiceStatus,
    OrderCommercialSnapshot,
    OrderCommercialStatus,
    OrderStatusEvent,
)
from app.services.commercial_service import create_order_and_invoice_atomic

ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture(scope='module', autouse=True)
def ensure_commercial_tables(test_db_engine):
    Base.metadata.create_all(bind=test_db_engine)


@pytest.fixture
def s08_client(db_session) -> TestClient:
    """Mounts auth + standalone S08 routers onto an isolated FastAPI app without modifying main.py."""
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(orders_router)
    app.include_router(invoices_router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, base_url='http://127.0.0.1:8000')


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        '/api/auth/login',
        json={'email': email, 'password': password},
        headers={'Origin': ORIGIN},
    )
    assert resp.status_code == 200, resp.text
    csrf_token = resp.json().get('csrf_token')
    assert csrf_token
    return csrf_token


def _seed_order_and_invoice(db_session, customer, *, quotation_id=None, product_summary='Housing Pattern — Cast Iron'):
    order, snapshot, invoice = create_order_and_invoice_atomic(
        db_session,
        customer_id=customer.id,
        customer_name='Apex Castings Ltd',
        customer_gstin='24AAACA1234A1Z5',
        customer_address='Plot 12, GIDC Vatva, Ahmedabad',
        product_summary=product_summary,
        items=[
            {
                'description': 'Housing Pattern (Cast Iron)',
                'quantity': 2,
                'unit': 'pcs',
                'unit_price': Decimal('50000.00'),
            },
            {
                'description': 'Machining & Finishing',
                'quantity': 1,
                'unit': 'lot',
                'unit_price': Decimal('20000.00'),
            },
        ],
        tax_rate_percent=Decimal('18.00'),
        quotation_id=quotation_id,
        quotation_version=2 if quotation_id is not None else None,
        estimated_lead_time_days=14,
    )
    db_session.commit()
    return order, snapshot, invoice


def test_atomic_order_invoice_creation_and_idempotency(db_session, test_users):
    u_c1 = test_users['customer_1']

    order1, snap1, inv1 = _seed_order_and_invoice(db_session, u_c1, quotation_id=9001)
    assert order1.status == OrderCommercialStatus.AWAITING_PAYMENT.value
    assert snap1.subtotal_amount == Decimal('120000.00')
    assert snap1.tax_amount == Decimal('21600.00')
    assert snap1.total_amount == Decimal('141600.00')
    assert inv1.order_id == order1.id
    assert inv1.is_demo_invoice is True
    assert inv1.status == InvoiceStatus.UNPAID.value

    # Repeating creation for the same quotation_id must return the exact same records
    order2, snap2, inv2 = _seed_order_and_invoice(db_session, u_c1, quotation_id=9001)
    assert order2.id == order1.id
    assert snap2.id == snap1.id
    assert inv2.id == inv1.id

    orders = db_session.scalars(select(Order).where(Order.customer_id == u_c1.id)).all()
    invoices = db_session.scalars(select(CommercialInvoice).where(CommercialInvoice.customer_id == u_c1.id)).all()
    assert len(orders) == 1
    assert len(invoices) == 1


def test_atomic_creation_rollback_on_invalid_items(db_session, test_users):
    u_c1 = test_users['customer_1']

    with pytest.raises(ValueError):
        create_order_and_invoice_atomic(
            db_session,
            customer_id=u_c1.id,
            customer_name='Apex Castings Ltd',
            product_summary='Broken Item',
            items=[{'description': 'Bad Qty', 'quantity': 0, 'unit_price': Decimal('100.00')}],
        )

    assert db_session.scalars(select(Order)).all() == []
    assert db_session.scalars(select(OrderCommercialSnapshot)).all() == []
    assert db_session.scalars(select(CommercialInvoice)).all() == []


def test_owner_admin_access_and_cross_customer_isolation(s08_client, db_session, test_users):
    u_c1 = test_users['customer_1']
    order, _, invoice = _seed_order_and_invoice(db_session, u_c1)

    # Owning customer can list and inspect order & invoice
    _login(s08_client, 'customer.one@example.test', 'Customer@12345')
    r_list = s08_client.get('/api/orders')
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1
    assert r_list.json()[0]['order_number'] == order.order_number
    assert r_list.json()[0]['production_status'] is None  # S08 boundary: no invented job status
    assert r_list.json()[0]['can_cancel'] is True

    r_detail = s08_client.get(f'/api/orders/{order.id}')
    assert r_detail.status_code == 200
    assert Decimal(r_detail.json()['total_amount']) == Decimal('141600.00')
    assert r_detail.json()['invoice']['invoice_number'] == invoice.invoice_number

    r_inv = s08_client.get(f'/api/invoices/{invoice.id}')
    assert r_inv.status_code == 200
    assert r_inv.json()['is_demo_invoice'] is True
    assert Decimal(r_inv.json()['outstanding_balance']) == Decimal('141600.00')

    # Second unrelated customer cannot see or download U-C1's records
    _login(s08_client, 'customer.two@example.test', 'Customer@12345')
    assert s08_client.get('/api/orders').json() == []
    assert s08_client.get(f'/api/orders/{order.id}').status_code == 403
    assert s08_client.get(f'/api/invoices/{invoice.id}').status_code == 403
    assert s08_client.get(f'/api/invoices/{invoice.id}/download').status_code == 403

    # Employee is blocked from commercial order/invoice endpoints
    _login(s08_client, 'employee.one@example.test', 'Employee@12345')
    assert s08_client.get('/api/orders').status_code == 403
    assert s08_client.get('/api/invoices').status_code == 403

    # Admin can inspect and download
    _login(s08_client, 'admin.one@example.test', 'Admin@12345')
    admin_orders = s08_client.get('/api/orders')
    assert admin_orders.status_code == 200
    assert len(admin_orders.json()) == 1
    assert admin_orders.json()[0]['can_cancel'] is False  # Only owning customer cancels
    assert s08_client.get(f'/api/invoices/{invoice.id}/download').status_code == 200


def test_demo_invoice_download_and_snapshot_immutability(s08_client, db_session, test_users):
    u_c1 = test_users['customer_1']

    # Create a catalogue product, create order/invoice, then mutate & deactivate the product
    product = Product(
        name='Housing Pattern (Cast Iron)',
        slug='housing-pattern-cast-iron',
        material_type='Cast Iron',
        indicative_price=Decimal('50000.00'),
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()

    order, _, invoice = _seed_order_and_invoice(db_session, u_c1)

    # Mutate and deactivate the catalogue product afterwards (AC-02-05 / AC-06-06)
    product.indicative_price = Decimal('99999.00')
    product.name = 'Renamed Pattern'
    product.is_active = False
    db_session.commit()

    _login(s08_client, 'customer.one@example.test', 'Customer@12345')

    # Download twice — must return immutable snapshot and never create a duplicate invoice
    dl1 = s08_client.get(f'/api/invoices/{invoice.id}/download')
    dl2 = s08_client.get(f'/api/invoices/{invoice.id}/download')
    assert dl1.status_code == 200
    assert dl2.status_code == 200
    assert 'attachment; filename="KPC-' in dl1.headers['content-disposition']
    assert dl1.headers['content-type'] == 'application/pdf'
    assert dl1.headers['content-disposition'].endswith('.pdf"')
    assert dl1.content.startswith(b'%PDF-')
    body = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(dl1.content)).pages).replace(',', '')
    assert 'INVOICE' in body
    assert 'DEMONSTRATION' not in body
    assert 'Housing Pattern (Cast Iron)' in body
    assert 'INR 120000.00' in body
    assert 'INR 21600.00' in body
    assert 'INR 141600.00' in body
    assert '99999.00' not in body
    assert 'Renamed Pattern' not in body

    all_invoices = db_session.scalars(select(CommercialInvoice)).all()
    assert len(all_invoices) == 1


def test_cancel_unpaid_order_preserves_history_and_blocks_paid_orders(s08_client, db_session, test_users):
    u_c1 = test_users['customer_1']
    unpaid_order, _, unpaid_invoice = _seed_order_and_invoice(db_session, u_c1)

    # Second customer cannot cancel U-C1's order
    csrf_c2 = _login(s08_client, 'customer.two@example.test', 'Customer@12345')
    r_other = s08_client.post(
        f'/api/orders/{unpaid_order.id}/cancel',
        json={'reason': 'Unauthorized attempt'},
        headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf_c2},
    )
    assert r_other.status_code == 403

    # Missing CSRF rejected
    csrf_c1 = _login(s08_client, 'customer.one@example.test', 'Customer@12345')
    r_no_csrf = s08_client.post(
        f'/api/orders/{unpaid_order.id}/cancel',
        json={'reason': 'Missing csrf'},
        headers={'Origin': ORIGIN},
    )
    assert r_no_csrf.status_code == 403

    # Valid zero-payment cancellation succeeds
    r_cancel = s08_client.post(
        f'/api/orders/{unpaid_order.id}/cancel',
        json={'reason': 'Project schedule postponed'},
        headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf_c1},
    )
    assert r_cancel.status_code == 200, r_cancel.text
    payload = r_cancel.json()['order']
    assert payload['status'] == OrderCommercialStatus.CANCELLED.value
    assert payload['can_cancel'] is False
    assert payload['cancellation_reason'] == 'Project schedule postponed'
    assert payload['invoice']['status'] == InvoiceStatus.CANCELLED.value
    assert [ev['event_type'] for ev in payload['status_history']] == ['order_created', 'order_cancelled']

    # Repeating cancellation (e.g. retry after a lost response) returns the saved state
    r_repeat = s08_client.post(
        f'/api/orders/{unpaid_order.id}/cancel',
        json={'reason': 'Second cancel'},
        headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf_c1},
    )
    assert r_repeat.status_code == 200, r_repeat.text
    repeat = r_repeat.json()['order']
    assert repeat['cancellation_reason'] == 'Project schedule postponed'
    assert [ev['event_type'] for ev in repeat['status_history']] == ['order_created', 'order_cancelled']

    # Controlled fixture: partially paid order CANNOT be cancelled (REQ-21 / AC-06-07)
    paid_order, paid_snap, paid_inv = _seed_order_and_invoice(db_session, u_c1)
    paid_snap.paid_amount = Decimal('25000.00')
    paid_snap.successful_payment_count = 1
    paid_inv.paid_amount = Decimal('25000.00')
    paid_inv.status = InvoiceStatus.PARTIALLY_PAID.value
    db_session.commit()

    r_paid_cancel = s08_client.post(
        f'/api/orders/{paid_order.id}/cancel',
        json={'reason': 'Try cancel after partial payment'},
        headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf_c1},
    )
    assert r_paid_cancel.status_code == 409
    assert r_paid_cancel.json()['detail']['code'] == 'CANCELLATION_NOT_ALLOWED'

    # Verify history events persisted
    events = db_session.scalars(select(OrderStatusEvent).where(OrderStatusEvent.order_id == unpaid_order.id)).all()
    assert len(events) == 2
