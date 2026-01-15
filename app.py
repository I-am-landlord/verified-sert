import streamlit as st
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- ТЕСТОВІ ДАНІ (Замість Excel) ---
DB = [
    {"id": "0001", "name": "Олександр Петренко", "instructor": "Дмитро Майстер", "date": "12.01.2025"},
    {"id": "0002", "name": "Марія Сидоренко", "instructor": "Олена Профі", "date": "15.05.2021"},
    {"id": "0003", "name": "Іван Іваненко", "instructor": "Дмитро Майстер", "date": "20.12.2024"},
]

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ PDF ---
def create_pdf(data, status):
    pdf = FPDF()
    pdf.add_page()
    
    # Використовуємо стандартний шрифт (для деплою на Streamlit він підтягнеться автоматично)
    # Якщо на сервері не буде кириличних шрифтів, ми використаємо латиницю або вкажемо шлях
    pdf.set_font("Arial", size=12)
    
    # Рамка
    pdf.set_line_width(1)
    pdf.rect(5, 5, 200, 287)
    
    # Заголовок
    pdf.set_font("Arial", style='B', size=20)
    pdf.cell(190, 20, "CERTIFICATE VERIFICATION", ln=True, align='C')
    
    # Дані (на латиниці для 100% сумісності при деплої без шрифтів)
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(190, 10, f"Certificate ID: {data['id']}", ln=True)
    pdf.cell(190, 10, f"Participant: {data['name']}", ln=True)
    pdf.cell(190, 10, f"Instructor: {data['instructor']}", ln=True)
    pdf.cell(190, 10, f"Issue Date: {data['date']}", ln=True)
    pdf.cell(190, 10, f"Status: {status}", ln=True)
    
    # Хеш безпеки
    raw_hash = f"{data['id']}{data['name']}SECRET".encode()
    h = hashlib.sha256(raw_hash).hexdigest()[:10]
    pdf.set_font("Arial", size=8)
    pdf.text(10, 280, f"Security Hash: {h}")
    
    # QR-код
    qr_content = f"ID:{data['id']} | {data['name']} | {status}"
    qr = qrcode.make(qr_content)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    return pdf.output()

# --- ВЕБ-ІНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Верифікація Сертифікатів", page_icon="📜")

st.title("📜 Система перевірки сертифікатів")
st.write("Введіть номер вашого сертифіката для отримання офіційного звіту.")

# Захист від перебору (Rate Limiting)
if 'attempts' not in st.session_state:
    st.session_state.attempts = 0

cert_id = st.text_input("Номер сертифіката (наприклад, CERT-001):").strip()

if st.button("Перевірити"):
    if st.session_state.attempts >= 5:
        st.error("Забагато спроб. Будь ласка, спробуйте пізніше.")
    else:
        # Шукаємо в базі
        result = next((item for item in DB if item['id'] == cert_id), None)
        
        # Імітація затримки для захисту від ботів
        time.sleep(1)
        
        if result:
            # Розрахунок статусу
            issue_date = datetime.strptime(result['date'], "%d.%m.%Y")
            if datetime.now() <= issue_date + timedelta(days=3*365):
                status = "ACTIVE"
                st.success(f"✅ Сертифікат знайдено! Власник: {result['name']}")
            else:
                status = "EXPIRED"
                st.warning(f"⚠️ Термін дії сертифіката ({result['name']}) вийшов.")
            
            # Генерація PDF
            pdf_bytes = create_pdf(result, status)
            st.download_button(
                label="📥 Завантажити PDF підтвердження",
                data=pdf_bytes,
                file_name=f"Verification_{cert_id}.pdf",
                mime="application/pdf"
            )
            st.session_state.attempts = 0 # Скидаємо лічильник при успіху
        else:
            st.error("❌ Сертифікат не знайдено в базі даних.")
            st.session_state.attempts += 1