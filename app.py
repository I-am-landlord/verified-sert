import streamlit as st
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- ТЕСТОВІ ДАНІ (База даних) ---
DB = [
    {"id": "CERT-001", "name": "Олександр Петренко", "instructor": "Дмитро Майстер", "date": "12.01.2025"},
    {"id": "CERT-002", "name": "Марія Сидоренко", "instructor": "Олена Профі", "date": "15.05.2021"},
    {"id": "CERT-003", "name": "Іван Іваненко", "instructor": "Дмитро Майстер", "date": "20.12.2024"},
]

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ PDF ---
def create_pdf(data, status):
    pdf = FPDF()
    pdf.add_page()
    
    # Визначаємо шлях до шрифтів (Linux стандарт для Streamlit Cloud)
    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    font_bold_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    
    # Вибір шрифту в залежності від середовища
    if os.path.exists(font_path):
        pdf.add_font("Liberation", style="", fname=font_path)
        pdf.add_font("Liberation", style="B", fname=font_bold_path)
        pdf.set_font("Liberation", size=12)
        font_name = "Liberation"
    else:
        # Fallback для локального запуску на Windows
        pdf.set_font("Arial", size=12)
        font_name = "Arial"

    # ДИЗАЙН: Подвійна рамка
    pdf.set_line_width(0.5)
    pdf.rect(5, 5, 200, 287)
    pdf.set_line_width(1)
    pdf.rect(7, 7, 196, 283)
    
    # ЗАГОЛОВОК
    pdf.set_font(font_name, style='B', size=22)
    pdf.set_text_color(44, 62, 80)
    pdf.ln(20)
    pdf.cell(190, 15, text="ОФІЦІЙНЕ ПІДТВЕРДЖЕННЯ", ln=True, align='C')
    pdf.set_font(font_name, size=14)
    pdf.cell(190, 10, text="про проходження спеціалізованого тренінгу", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_draw_color(44, 62, 80)
    pdf.line(30, 65, 180, 65)
    pdf.ln(15)

    # ТАБЛИЦЯ ДАНИХ
    pdf.set_text_color(0, 0, 0)
    def add_row(label, value):
        pdf.set_font(font_name, style='B', size=12)
        pdf.set_x(30)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.set_font(font_name, size=12)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_row("Номер сертифікату", data['id'])
    add_row("Учасник", data['name'])
    add_row("Інструктор", data['instructor'])
    add_row("Дата видачі", data['date'])
    
    pdf.ln(10)
    
    # СТАТУС-БОКС
    is_active = "АКТИВНИЙ" in status
    bg_color = (46, 204, 113) if is_active else (231, 76, 60)
    pdf.set_fill_color(*bg_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(30)
    pdf.set_font(font_name, style='B', size=14)
    pdf.cell(150, 12, text=f"СТАТУС: {status}", ln=True, align='C', fill=True)

    # QR-КОД
    qr_text = f"Cert ID: {data['id']} | User: {data['name']} | Status: {status}"
    qr = qrcode.make(qr_text)
    qr_file = "temp_qr.png"
    qr.save(qr_file)
    pdf.image(qr_file, x=155, y=240, w=35)

    # ХЕШ БЕЗПЕКИ ТА ПЕЧАТКА
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_name, size=8)
    h = hashlib.sha256(f"{data['id']}{data['name']}".encode()).hexdigest()[:15]
    pdf.text(30, 280, f"Код автентичності: {h}")

    # СИНЯ ПЕЧАТКА
    pdf.set_draw_color(0, 51, 153)
    pdf.set_text_color(0, 51, 153)
    pdf.circle(45, 245, 18)
    pdf.set_font(font_name, size=6)
    pdf.text(35, 243, "ВЕРИФІКОВАНО")
    pdf.text(38, 247, "E-SYSTEM")
    
    if os.path.exists(qr_file):
        os.remove(qr_file)
        
    return pdf.output()

# --- STREAMLIT ІНТЕРФЕЙС ---
st.set_page_config(page_title="Verify System", page_icon="🛡️")

st.title("🛡️ Верифікація сертифікатів")
st.markdown("---")

# Ініціалізація захисту від перебору
if 'attempts' not in st.session_state:
    st.session_state.attempts = 0

cert_id = st.text_input("Введіть номер сертифіката:").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    if st.session_state.attempts >= 5:
        st.error("❌ Доступ заблоковано через забагато невдалих спроб.")
    else:
        # Пошук
        result = next((item for item in DB if item['id'] == cert_id), None)
        
        # Затримка для безпеки
        with st.spinner('Пошук у реєстрі...'):
            time.sleep(1.2)
        
        if result:
            st.session_state.attempts = 0
            # Розрахунок терміну дії (3 роки)
            issue_date = datetime.strptime(result['date'], "%d.%m.%Y")
            is_valid = datetime.now() <= issue_date + timedelta(days=3*365)
            status_text = "АКТИВНИЙ" if is_valid else "ТЕРМІН ДІЇ ВИЙШОВ"
            
            st.success(f"✅ Документ знайдено: {result['name']}")
            
            # Генерація PDF
            try:
                pdf_output = create_pdf(result, status_text)
                st.download_button(
                    label="📥 Завантажити PDF-підтвердження",
                    data=bytes(pdf_output),
                    file_name=f"Verified_{cert_id}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Помилка генерації PDF: {e}")
        else:
            st.error("❌ Сертифікат з таким номером не знайдено.")
            st.session_state.attempts += 1
