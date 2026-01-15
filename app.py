import streamlit as st
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- ТЕСТОВІ ДАНІ ---
DB = [
    {"id": "CERT-001", "name": "Oleksandr Petrenko", "instructor": "Dmytro Maister", "date": "12.01.2025"},
    {"id": "CERT-002", "name": "Mariia Sydorenko", "instructor": "Olena Profi", "date": "15.05.2021"},
    {"id": "CERT-003", "name": "Ivan Ivanenko", "instructor": "Dmytro Maister", "date": "20.12.2024"},
]

def create_pdf(data, status):
    pdf = FPDF()
    pdf.add_page()
    
    # Спроба знайти системні шрифти в різних популярних локаціях Linux
    possible_fonts = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    
    font_used = "Helvetica" # Default
    for fpath in possible_fonts:
        if os.path.exists(fpath):
            try:
                pdf.add_font("CustomFont", style="", fname=fpath)
                pdf.add_font("CustomFont", style="B", fname=fpath.replace("-Regular", "-Bold").replace(".ttf", "Bold.ttf"))
                pdf.set_font("CustomFont", size=12)
                font_used = "CustomFont"
                break
            except:
                continue
    
    if font_used == "Helvetica":
        pdf.set_font("Helvetica", size=12)

    # ДИЗАЙН: Рамка
    pdf.set_line_width(1)
    pdf.rect(5, 5, 200, 287)
    
    # ЗАГОЛОВОК
    pdf.set_font(font_used, style='B', size=20)
    pdf.ln(20)
    # Якщо шрифт Helvetica, використовуємо англійську мову для уникнення помилок
    header_text = "OFFICIAL CONFIRMATION" if font_used == "Helvetica" else "ОФІЦІЙНЕ ПІДТВЕРДЖЕННЯ"
    pdf.cell(190, 15, text=header_text, ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font(font_used, size=12)
    
    # Дані
    def add_row(label_ua, label_en, value):
        label = label_ua if font_used != "Helvetica" else label_en
        pdf.set_font(font_used, style='B', size=12)
        pdf.set_x(30)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.set_font(font_used, size=12)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_row("Номер сертифікату", "Certificate ID", data['id'])
    add_row("Учасник", "Participant", data['name'])
    add_row("Інструктор", "Instructor", data['instructor'])
    add_row("Дата видачі", "Issue Date", data['date'])
    add_row("Статус", "Status", status)
    
    # QR-код
    qr_text = f"Verify: {data['id']} | {data['name']}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    # Хеш
    h = hashlib.sha256(f"{data['id']}".encode()).hexdigest()[:12]
    pdf.set_font(font_used, size=8)
    pdf.text(30, 280, f"Verification Code: {h}")

    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- STREAMLIT ---
st.set_page_config(page_title="Verifier", page_icon="🛡️")
st.title("🛡️ Certificate Verifier")

cert_id = st.text_input("Enter ID (CERT-001):").strip().upper()

if st.button("Verify"):
    result = next((item for item in DB if item['id'] == cert_id), None)
    if result:
        # Статус англійською для сумісності
        status = "ACTIVE"
        st.success(f"✅ Found: {result['name']}")
        
        pdf_out = create_pdf(result, status)
        st.download_button(
            label="📥 Download PDF Report",
            data=bytes(pdf_out),
            file_name=f"Verified_{cert_id}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ Not found.")
