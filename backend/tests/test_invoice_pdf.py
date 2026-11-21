from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader

from app.schemas.commercial import CommercialLineItem, InvoiceDetailResponse
from app.services.invoice_pdf import render_invoice_pdf


def invoice(items):
    total = sum(item.line_total for item in items)
    return InvoiceDetailResponse(id=1, invoice_number='INV-2026-000001', order_id=1,
        order_number='KPC-2026-000001', customer_id=1, customer_name='Tools <drawing> & Castings',
        subtotal_amount=total, tax_rate_percent=0, tax_amount=0, total_amount=total,
        paid_amount=0, outstanding_balance=total, status='unpaid', issued_at=datetime.now(timezone.utc),
        order_status='awaiting_payment', items=items)


def test_pdf_escapes_stored_text_and_preserves_exact_money():
    detail = invoice([CommercialLineItem(description='Tooling <drawing> & finish', quantity=1, unit_price='123456.78', line_total='123456.78')])
    raw = render_invoice_pdf(detail)
    assert raw.startswith(b'%PDF-')
    reader = PdfReader(BytesIO(raw))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert 'Tooling <drawing> & finish' in text and 'Tools <drawing> & Castings' in text
    assert 'INR 123,456.78' in text and 'No payments recorded.' in text
    assert not any(word in text.lower() for word in ['demo', 'simulat', 'academic'])


def test_long_invoice_paginates_without_losing_rows_or_final_totals():
    detail = invoice([CommercialLineItem(description=f'Pattern {i+1}: '+('Dimensional inspection and machining requirements. '*8),
        quantity=1, unit_price='1000', line_total='1000') for i in range(50)])
    reader = PdfReader(BytesIO(render_invoice_pdf(detail)))
    assert len(reader.pages) > 1
    text = '\n'.join(page.extract_text() for page in reader.pages)
    for i in range(50):
        assert f'Pattern {i+1}:' in text
    assert 'INR 50,000.00' in text and 'Payment history' in text
    assert text.count('Description') > 1
    assert f'Page {len(reader.pages)}' in text
