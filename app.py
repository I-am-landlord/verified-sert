import streamlit as st
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- БАЗА ДАНИХ (6 ТЕСТОВИХ ЗАПИСІВ) ---
# Формат дати: РРРР-ММ-ДД для зручності розрахунків
DB = [
    {"id": "CERT-001", "name": "Олександр Петренко", "instructor": "Дмитро Майстер", "date": "2025-01-12"},
    {"id": "CERT-002", "name": "Марія Сидоренко", "instructor": "Олена Профі", "date": "2021-05-15"}, # Прострочений
    {"id": "CERT-003", "name": "Іван Іваненко", "instructor": "Дмитро Майстер", "date": "2024-12-20"},
    {"id": "CERT-004", "name": "Ганна Коваль", "instructor": "Олена Профі", "date": "2023-02-15"}, # Скоро закінчується (якщо термін 3 роки - ні, але ми налаштуємо тест)
    {"id": "CERT-005", "name": "Петро Щур", "instructor": "Ігор Технік", "date": "2022-02-01"}, # Скоро закінчується (3 роки закінчуються 2025-02-01)
    {"id": "CERT-006", "name": "Світлана Линник", "instructor": "Ігор Технік", "date": "2025-01-10"},
]

def create_pdf(data, status, expiry_date):
    pdf = FPDF()
    pdf.add_page()
    
    font_filename = "dejavu-sans.book.ttf" # Переконайтеся, що назва на GitHub збігається!
    
    if os.path.exists(font_filename):
        pdf.add_font("DejaVu", style="", fname=font_filename)
        pdf.set_font("DejaVu", size=12)
        font_name = "DejaVu"
    else:
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    # Рамка
    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287)
    
    # Заголовок
    pdf.set_font(font_name, size=22)
    pdf.set_text_color(44, 62, 80)
    pdf.ln(20)
    pdf.cell(190, 15, text="ОФІЦІЙНЕ ПІДТВЕРДЖЕННЯ", ln=True, align='C')
    
    pdf.set_draw_color(44, 62, 80)
    pdf.line(40, 60, 170, 60)
    pdf.ln(15)
    
    # Дані
    def add_row(label, value):
        pdf.set_font(font_name, size=12)
        pdf.set_x(30)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_row("Номер сертифікату", data['id'])
    add_row("Учасник", data['name'])
    add_row("Інструктор", data['instructor'])
    add_row("Дата видачі", data['date'])
    add_row("Дійсний до", expiry_date.strftime('%d.%m.%Y'))
    add_row("Статус", status)
    
    # QR-код
    qr_text = f"ID:{data['id']} | {data['name']} | Exp:{expiry_date.strftime('%Y-%m-%d')}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    # Хеш
    h = hashlib.sha256(f"{data['id']}".encode()).hexdigest()[:15]
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.text(30, 280, f"Digital Sign: {h}")

    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- STREAMLIT ІНТЕРФЕЙС ---
st.set_page_config(page_title="Verify Center", page_icon="🛡️")

st.title("🛡️ Верифікація сертифікатів")
st.write("Введіть номер для перевірки даних у реєстрі.")

cert_id = st.text_input("Номер сертифіката (наприклад, CERT-005):").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    result = next((item for item in DB if item['id'] == cert_id), None)
    
    if result:
        # Розрахунок термінів
        issue_date = datetime.strptime(result['date'], "%Y-%m-%d")
        expiry_date = issue_date + timedelta(days=3*365)
        days_left = (expiry_date - datetime.now()).days
        
        # Визначення статусу
        if days_left < 0:
            status = "ТЕРМІН ДІЇ ВИЙШОВ"
            st.error(f"❌ Сертифікат {cert_id} більше не дійсний.")
        elif days_left <= 30:
            status = "ПОТРЕБУЄ ОНОВЛЕННЯ"
            st.warning(f"⚠️ Увага! Термін дії закінчується через {days_left} дн. Рекомендуємо пройти повторне навчання.")
        else:
            status = "АКТИВНИЙ"
            st.success(f"✅ Сертифікат дійсний ще {days_left} дн.")
        
        # --- ВІДОБРАЖЕННЯ ДАНИХ НА СТОРІНЦІ ---
        st.markdown("### 📋 Детальна інформація:")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Власник:** {result['name']}")
            st.write(f"**Інструктор:** {result['instructor']}")
            st.write(f"**ID:** {result['id']}")
            
        with col2:
            st.write(f"**Дата видачі:** {issue_date.strftime('%d.%m.%Y')}")
            st.write(f"**Дійсний до:** {expiry_date.strftime('%d.%m.%Y')}")
            st.write(f"**Статус:** {status}")

        # Генерація PDF
        pdf_out = create_pdf(result, status, expiry_date)
        st.download_button(
            label="📥 Завантажити PDF підтвердження",
            data=bytes(pdf_out),
            file_name=f"Verified_{cert_id}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ Сертифікат не знайдено в базі даних. Перевірте правильність номеру.")

# Секція для тестування (можна приховати)
with st.expander("Довідка по тестовим ID"):
    st.write("CERT-001 - Активний")
    st.write("CERT-002 - Прострочений (2021 рік)")
    st.write("CERT-005 - Закінчується скоро (лютий 2025)")
