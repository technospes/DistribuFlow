import os
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.database.models import Order, Invoice, Distributor
from app.repositories import order_repository

# Ensure a directory exists to store the PDFs
INVOICE_DIR = os.path.join(os.getcwd(), "invoices_store")
os.makedirs(INVOICE_DIR, exist_ok=True)

def generate_invoice_pdf(db: Session, order_id: UUID, generated_by: str = "System") -> Invoice:
    """
    Generates a PDF invoice for an approved order and saves the record to the database.
    (Business Rules Rule 6: Generate on approval, do not send yet).
    """
    # 1. Fetch the Order and Distributor
    order = order_repository.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "Approved":
         raise HTTPException(status_code=400, detail="Invoices can only be generated for Approved orders.")

    # IDEMPOTENCY CHECK: If an invoice already exists, return it immediately.
    existing_invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    if existing_invoice:
        return existing_invoice

    # 2. Generate the unique Invoice Number (INV-YYYYMMDD-NNNNN)
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"INV-{today_str}-"
    
    # Simple sequence logic for MVP (similar to order generation)
    last_invoice = db.query(Invoice).filter(Invoice.invoice_number.like(f"{prefix}%")).order_by(Invoice.invoice_number.desc()).first()
    new_sequence = int(last_invoice.invoice_number.split("-")[-1]) + 1 if last_invoice else 1
    invoice_number = f"{prefix}{new_sequence:05d}"
    
    # 3. Setup the PDF Document
    file_path = os.path.join(INVOICE_DIR, f"{invoice_number}.pdf")
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # --- Header ---
    elements.append(Paragraph("<b>TAX INVOICE</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph(f"<b>Invoice Number:</b> {invoice_number}", styles['Normal']))
    elements.append(Paragraph(f"<b>Order Number:</b> {order.order_number}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # --- Distributor Details ---
    distributor = order.distributor
    elements.append(Paragraph(f"<b>Billed To:</b>", styles['Heading3']))
    elements.append(Paragraph(f"{distributor.company_name or 'N/A'}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {distributor.phone_number}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # --- Item Table ---
    data = [["SKU", "Quantity", "Price", "Subtotal"]]
    for item in order.items:
        data.append([
            item.product.sku,
            str(item.quantity_cartons),
            f"Rs {item.price}",
            f"Rs {item.subtotal}"
        ])
    
    # Add Total Row
    data.append(["", "", "Total:", f"Rs {order.total_amount}"])

    table = Table(data, colWidths=[200, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    # 4. Build the PDF
    doc.build(elements)

    # 5. Save Record to Database
    db_invoice = Invoice(
        order_id=order.id,
        invoice_number=invoice_number,
        file_path=file_path,
        generated_by=generated_by,
        sent_to_distributor=False # Rule 6: Do not send automatically
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    return db_invoice