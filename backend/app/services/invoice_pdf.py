"""Printable invoice generated solely from the stored commercial record."""
from datetime import timezone
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.commercial import InvoiceDetailResponse

NAVY = colors.HexColor('#062449')
ORANGE = colors.HexColor('#f58200')
MUTED = colors.HexColor('#60738f')
LINE = colors.HexColor('#dbe4f0')


def render_invoice_pdf(detail: InvoiceDetailResponse) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=42, leftMargin=42,
        topMargin=40, bottomMargin=48, title=f'Invoice {detail.invoice_number}', author='Khodel Pattern Craft')
    styles = getSampleStyleSheet()
    body = ParagraphStyle('InvoiceBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9,
        leading=13, textColor=NAVY, spaceAfter=3)
    heading = ParagraphStyle('InvoiceHeading', parent=body, fontName='Helvetica-Bold', fontSize=12, leading=17, spaceAfter=9)
    right = ParagraphStyle('InvoiceRight', parent=body, alignment=TA_RIGHT)
    muted = ParagraphStyle('InvoiceMuted', parent=body, fontSize=8, textColor=MUTED)
    brand = ParagraphStyle('InvoiceBrand', parent=heading, fontSize=30, leading=34)
    title = ParagraphStyle('InvoiceTitle', parent=heading, fontSize=22, leading=26, alignment=TA_RIGHT)

    def p(value, style=body):
        # Stored names, addresses and descriptions are plain text, never PDF markup.
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), style)

    def money(value):
        return f'INR {value:,.2f}'

    def date(value, include_time=False):
        if value is None:
            return 'Not specified'
        value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return value.strftime('%d %b %Y, %H:%M UTC' if include_time else '%d %b %Y')

    header = Table([
        [[p('KPC', brand), p('KHODEL PATTERN CRAFT', muted)], p('INVOICE', title)],
        [p('Industrial Pattern Manufacturing', muted), p(detail.invoice_number, right)],
    ], colWidths=[doc.width * .52, doc.width * .48])
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('LINEBELOW', (0, -1), (-1, -1), 2, ORANGE),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 14)]))
    story = [header, Spacer(1, 20)]
    billing = [p('BILL TO', heading), p(detail.customer_name)]
    if detail.customer_address:
        billing.append(p(detail.customer_address))
    if detail.customer_gstin:
        billing.append(p(f'GSTIN: {detail.customer_gstin}'))
    metadata = [p(f'Order: {detail.order_number}', right), p(f'Issued: {date(detail.issued_at)}', right),
        p(f'Due: {date(detail.due_at)}', right), p(f'Status: {detail.status.replace("_", " ").title()}', right)]
    billing_table = Table([[billing, metadata]], colWidths=[doc.width * .55, doc.width * .45])
    billing_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story.extend([billing_table, Spacer(1, 20)])

    def table(rows, widths):
        result = LongTable(rows, colWidths=widths, repeatRows=1, splitInRow=0, hAlign='LEFT')
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef3f8')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, LINE),
            ('LINEBELOW', (0, 1), (-1, -1), .5, LINE),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ]))
        return result

    rows = [[p('#'), p('Description'), p('Qty', right), p('Unit price', right), p('Amount', right)]]
    for index, item in enumerate(detail.items, 1):
        rows.append([p(index), p(item.description), p(f'{item.quantity} {item.unit}', right), p(money(item.unit_price), right), p(money(item.line_total), right)])
    story.extend([table(rows, [34, doc.width - 34 - 52 - 111 - 123, 52, 111, 123]), Spacer(1, 16)])
    totals = Table([[p(label), p(value, right)] for label, value in [
        ('Subtotal', money(detail.subtotal_amount)), (f'Tax ({detail.tax_rate_percent:.2f}%)', money(detail.tax_amount)),
        ('Total', money(detail.total_amount)), ('Paid', money(detail.paid_amount)), ('Balance due', money(detail.outstanding_balance)),
    ]], colWidths=[130, 156], hAlign='RIGHT')
    totals.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 2), (-1, 2), 1, NAVY), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff2df'))]))
    story.append(KeepTogether([totals, Spacer(1, 24)]))
    history = [[p('Reference'), p('Recorded at'), p('Status'), p('Recorded by'), p('Amount', right)]]
    for payment in detail.payments:
        history.append([p(f'PAY-{payment.id}'), p(date(payment.created_at, True)),
            p('Completed' if payment.outcome == 'succeeded' else 'Failed'), p(f'User #{payment.actor_user_id}'), p(money(payment.amount), right)])
    if not detail.payments:
        history.append([p('No payments recorded.'), '', '', '', ''])
    history_table = table(history, [65, doc.width - 65 - 65 - 72 - 123, 65, 72, 123])
    if not detail.payments:
        history_table.setStyle(TableStyle([('SPAN', (0, 1), (-1, 1))]))
    story.extend([p('Payment history', heading), history_table,
        Spacer(1, 16), p('Please quote the invoice number when referencing this invoice or its payments.', muted)])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(42, 34, A4[0] - 42, 34)
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(42, 22, 'KPC | Khodel Pattern Craft')
        canvas.drawRightString(A4[0] - 42, 22, f'Page {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
