import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import hashlib
import time
from datetime import datetime, timedelta
from fpdf import FPDF

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Verify Center", page_icon="🛡️")

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ PDF ---
def create_pdf(data, status, expiry_date):
    pdf = FPDF()
    pdf.add_page()
    
    font_filename = "DejaVuSans.ttf" 
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
    qr_text = f"ID:{data['id']} | Name:{data['name']} | Status:{status}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    
    # Хеш
    h = hashlib.sha256(str(data['id']).encode()).hexdigest()[:15]
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.text(30, 280, f"Код автентичності: {h}")

    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- ОСНОВНА ЛОГІКА ДОДАТКА ---
st.title("🛡️ Верифікація сертифікатів")
st.write("Синхронізація з реєстром Google Sheets")

# Підключення до Google Sheets
# Використовуємо URL безпосередньо в коді для надійності
# ЗАМІНІТЬ ЦЕ ПОСИЛАННЯ НА ВАШЕ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1X-uO39m7L8O4S8_8h6Bq9A2O3_mS8E2o/edit#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Спроба прочитати таблицю (використовуємо посилання з коду або з secrets)
    df = conn.read(spreadsheet=SHEET_URL)
    
    # ОЧИЩЕННЯ ТА ПІДГОТОВКА ДАНИХ
    df.columns = df.columns.str.strip().str.lower() # Очищаємо назви колонок
    df = df.dropna(subset=['id']) # Видаляємо порожні ID
    df['id'] = df['id'].astype(str).str.strip().str.upper() # Примусово в текст
except Exception as e:
    st.error(f"⚠️ Помилка підключення: {e}")
    st.stop()

# Поле вводу
cert_id_input = st.text_input("Введіть номер сертифіката (наприклад, 2105):").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    if not cert_id_input:
        st.warning("Будь ласка, введіть номер документа.")
    else:
        # Пошук співпадіння
        match = df[df['id'] == cert_id_input]
        
        if not match.empty:
            result = match.iloc[0].to_dict()
            
            # Обробка дати
            try:
                # Обробка різних форматів дати (02.01.26 або 2026-01-02)
                issue_date = pd.to_datetime(result['date'], dayfirst=True).to_pydatetime()
            except:
                st.error("❌ Помилка формату дати в таблиці. Використовуйте ДД.ММ.РРРР")
                st.stop()

            expiry_date = issue_date + timedelta(days=3*365)
            days_left = (expiry_date - datetime.now()).days
            
            # Визначення статусу
            if days_left < 0:
                status = "ТЕРМІН ДІЇ ВИЙШОВ"
                st.error(f"❌ Сертифікат {cert_id_input} більше не дійсний.")
            elif days_left <= 30:
                status = "ПОТРЕБУЄ ОНОВЛЕННЯ"
                st.warning(f"⚠️ Увага! Термін дії закінчується через {max(0, days_left)} дн. Рекомендуємо перепідготовку.")
            else:
                status = "АКТИВНИЙ"
                st.success(f"✅ Документ знайдено. Дійсний ще {days_left} дн.")
            
            # Вивід даних на екран
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"👤 **Учасник:** {result['name']}")
                st.write(f"🆔 **ID:** {result['id']}")
            with col2:
                st.write(f"📅 **Дата видачі:** {issue_date.strftime('%d.%m.%Y')}")
                st.write(f"🎓 **Інструктор:** {result['instructor']}")
            
            # PDF за запитом
            pdf_bytes = create_pdf(result, status, expiry_date)
            st.download_button(
                label="📥 Завантажити PDF підтвердження",
                data=bytes(pdf_bytes),
                file_name=f"Verified_{cert_id_input}.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"❌ Сертифікат '{cert_id_input}' не знайдено в базі даних.")
            # Допомога для тестування (можна приховати)
            with st.expander("Переглянути доступні ID (для тесту)"):
                st.write(df['id'].unique())
