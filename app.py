import streamlit as st
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- БАЗА ДАНИХ (Кирилиця працюватиме) ---
DB = [
    {"id": "CERT-001", "name": "Олександр Петренко", "instructor": "Дмитро Майстер", "date": "12.01.2025"},
    {"id": "CERT-002", "name": "Марія Сидоренко", "instructor": "Олена Профі", "date": "15.05.2021"},
    {"id": "CERT-003", "name": "Іван Іваненко", "instructor": "Дмитро Майстер", "date": "20.12.2024"},
]

def create_pdf(data, status):
    pdf = FPDF()
    pdf.add_page()
    
    # ПЕРЕВІРТЕ НАЗВУ ФАЙЛУ! 
    # Якщо на GitHub файл називається "DejaVuSans.ttf", то в лапках має бути так само.
    font_filename = "dejavu-sans.book.ttf" 
    
    if os.path.exists(font_filename):
        pdf.add_font("DejaVu", style="", fname=font_filename)
        pdf.set_font("DejaVu", size=12)
        font_name = "DejaVu"
    else:
        # Якщо файл не знайдено, виводимо помилку на екран Streamlit
        st.error(f"Файл шрифту '{font_filename}' не знайдено в репозиторії!")
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    # --- ДИЗАЙН ДОКУМЕНТА ---
    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287) # Рамка
    
    # Заголовок
    pdf.set_font(font_name, size=22)
    pdf.set_text_color(44, 62, 80)
    pdf.ln(20)
    pdf.cell(190, 15, text="ПІДТВЕРДЖЕННЯ СЕРТИФІКАТУ", ln=True, align='C')
    
    pdf.set_draw_color(44, 62, 80)
    pdf.line(40, 60, 170, 60)
    pdf.ln(15)
    
    # Блок даних
    pdf.set_text_color(0, 0, 0)
    def add_row(label, value):
        pdf.set_font(font_name, size=12) # Жирний можна додати, якщо завантажити DejaVuSans-Bold.ttf
        pdf.set_x(30)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_row("Номер сертифікату", data['id'])
    add_row("Учасник", data['name'])
    add_row("Інструктор", data['instructor'])
    add_row("Дата видачі", data['date'])
    add_row("Статус", status)
    
    # QR-код
    qr_text = f"Верифікація сертифікату {data['id']}\nВласник: {data['name']}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    # Хеш безпеки (Security Hash)
    h = hashlib.sha256(f"{data['id']}{data['name']}".encode()).hexdigest()[:15]
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.text(30, 280, f"Цифровий підпис верифікації: {h}")

    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- STREAMLIT ---
st.set_page_config(page_title="Сертифікати", page_icon="🛡️")

st.title("🛡️ Верифікація сертифікатів")
st.write("Система миттєвої перевірки автентичності документів")

cert_id = st.text_input("Введіть номер сертифіката (наприклад, CERT-001):").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    result = next((item for item in DB if item['id'] == cert_id), None)
    
    if result:
        # Логіка статусу
        status = "АКТИВНИЙ" 
        st.success(f"✅ Документ знайдено: {result['name']}")
        
        pdf_out = create_pdf(result, status)
        st.download_button(
            label="📥 Завантажити PDF підтвердження",
            data=bytes(pdf_out),
            file_name=f"Verified_{cert_id}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ Сертифікат не знайдено в базі даних.")
