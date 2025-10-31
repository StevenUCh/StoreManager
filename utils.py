import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

def export_to_csv(movimientos):
    df = pd.DataFrame([m.to_dict() for m in movimientos])
    return df.to_csv(index=False)

def export_to_pdf(movimientos, filename="reporte.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for mov in movimientos:
        c.drawString(50, y, f"{mov.fecha} | {mov.categoria} | {mov.monto}")
        y -= 20
    c.save()
    buffer.seek(0)
    return buffer

def import_from_csv(file):
    df = pd.read_csv(file)
    return df.to_dict(orient='records')
