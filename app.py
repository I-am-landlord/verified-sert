import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ PDF ---
def create_pdf(data, status, expiry_date):
    pdf = FPDF()
    pdf.add_page()
    
    # Використовуємо файл шрифту, який ви завантажили на GitHub
    font_filename = "DejaVuSans.ttf" 
    
    if os.path.exists(font_filename):
        pdf.add_font("DejaVu", style="", fname=font_filename)
        pdf.set_font("DejaVu", size=12)
        font_name = "DejaVu"
    else:
        st.error("Помилка: Файл DejaVuSans.ttf не знайдено на GitHub!")
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    # Дизайн: Рамка
    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287)
    
    # Заголовок
    pdf.set_font(font_name, size=22)
    pdf.set_text_color(44, 62, 80)
    pdf.ln(20)
    pdf.cell(190, 15, text="ОФІЦІЙНЕ ПІДТВЕРДЖЕННЯ", ln=True, align='C')
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
    qr_text = f"Верифікація: {data['id']} | Власник: {data['name']}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    # Хеш
    h = hashlib.sha256(f"{data['id']}".encode()).hexdigest()[:15]
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.text(30, 280, f"Код автентичності: {h}")

    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- STREAMLIT ІНТЕРФЕЙС ---
st.set_page_config(page_title="Verify Center", page_icon="🛡️")

st.title("🛡️ Верифікація сертифікатів")
st.write("Дані синхронізуються з Google Sheets")

# Підключення до Google Sheets (використовує Secrets)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    # Видаляємо пусті рядки, якщо вони є
    df = df.dropna(subset=['id'])
except Exception as e:
    st.error(f"Помилка підключення до таблиці: {e}")
    st.stop()

cert_id = st.text_input("Введіть номер сертифіката:").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    # Пошук у завантаженому DataFrame
    match = df[df['id'].astype(str).str.upper() == cert_id]
    
    if not match.empty:
        result = match.iloc[0].to_dict()
        
        # Розрахунок термінів (припускаємо формат дати в таблиці ДД.ММ.РРРР або РРРР-ММ-ДД)
        try:
            # Спроба автоматично розпізнати дату з таблиці
            issue_date = pd.to_datetime(result['date']).to_pydatetime()
        except:
            st.error("Помилка формату дати в таблиці. Використовуйте РРРР-ММ-ДД")
            st.stop()
            
        expiry_date = issue_date + timedelta(days=3*365)
        days_left = (expiry_date - datetime.now()).days
        
        # Логіка статусів
        if days_left < 0:
            status = "ТЕРМІН ДІЇ ВИЙШОВ"
            st.error(f"❌ Сертифікат {cert_id} більше не дійсний.")
        elif days_left <= 30:
            status = "ПОТРЕБУЄ ОНОВЛЕННЯ"
            st.warning(f"⚠️ Увага! Термін дії закінчується через {days_left} дн. Рекомендуємо повторне навчання.")
        else:
            status = "АКТИВНИЙ"
            st.success(f"✅ Сертифікат знайдено і він дійсний.")
        
        # Відображення на сторінці
        st.markdown("### 📋 Інформація про документ:")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Учасник:**\n{result['name']}")
            st.info(f"**ID:**\n{result['id']}")
        with col2:
            st.info(f"**Видано:**\n{issue_date.strftime('%d.%m.%Y')}")
            st.info(f"**Статус:**\n{status}")

        # Генерація PDF
        pdf_out = create_pdf(result, status, expiry_date)
        st.download_button(
            label="📥 Завантажити PDF підтвердження",
            data=bytes(pdf_out),
            file_name=f"Verified_{cert_id}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ Сертифікат не знайдено в реєстрі.")
