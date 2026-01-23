import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import hashlib
from datetime import datetime, timedelta
from fpdf import FPDF

# --- ФУНКЦІЯ PDF ---
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

    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287)
    pdf.set_font(font_name, size=22)
    pdf.ln(20)
    pdf.cell(190, 15, text="ОФІЦІЙНЕ ПІДТВЕРДЖЕННЯ", ln=True, align='C')
    
    def add_row(label, value):
        pdf.set_font(font_name, size=12)
        pdf.set_x(30)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_row("Номер сертифікату", data['id'])
    add_row("Учасник", data['name'])
    add_row("Інструктор", data['instructor'])
    add_row("Дата видачі", data['date'])
    add_row("Статус", status)
    
    qr_text = f"ID:{data['id']} | {data['name']}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=160, y=250, w=30)
    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- STREAMLIT ІНТЕРФЕЙС ---
st.set_page_config(page_title="Verify Center", page_icon="🛡️")
st.title("🛡️ Верифікація сертифікатів")

try:
    # Підключення: бере все автоматично з Secrets (включаючи посилання на таблицю)
    conn = st.connection("gsheets", type=GSheetsConnection)
    # TTL=600 означає, що дані оновлюватимуться кожні 10 хвилин
    df = conn.read(ttl=600)
    
    # ПІДГОТОВКА ДАНИХ (Data Cleaning)
    # 1. Видаляємо зайві пробіли в назвах колонок та переводимо в нижній регістр
    df.columns = df.columns.str.strip().str.lower()
    
    # 2. Перетворюємо ID на текст, прибираємо .0 (якщо Excel зробив число) і пробіли
    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    
    # 3. Видаляємо рядки, де ID пустий
    df = df[df['id'] != 'NAN']
    
except Exception as e:
    st.error(f"⚠️ Помилка завантаження даних: {e}")
    st.stop()

cert_id_input = st.text_input("Введіть номер сертифіката:").strip().upper()

if st.button("ПЕРЕВІРИТИ"):
    if cert_id_input:
        # Шукаємо в підготовленому DataFrame
        match = df[df['id'] == cert_id_input]
        
        if not match.empty:
            result = match.iloc[0].to_dict()
            
            # Розрахунок термінів
            try:
                issue_date = pd.to_datetime(result['date'], dayfirst=True).to_pydatetime()
                expiry_date = issue_date + timedelta(days=3*365)
                days_left = (expiry_date - datetime.now()).days
                
                if days_left < 0:
                    status = "ТЕРМІН ДІЇ ВИЙШОВ"
                    st.error(f"❌ Сертифікат {cert_id_input} прострочений.")
                elif days_left <= 30:
                    status = "ПОТРЕБУЄ ОНОВЛЕННЯ"
                    st.warning(f"⚠️ Закінчується через {days_left} дн.")
                else:
                    status = "АКТИВНИЙ"
                    st.success(f"✅ Сертифікат дійсний.")
                
                st.write(f"👤 **Учасник:** {result['name']}")
                st.write(f"📅 **Дата видачі:** {issue_date.strftime('%d.%m.%Y')}")
                
                pdf_bytes = create_pdf(result, status, expiry_date)
                st.download_button(
                    label="📥 Завантажити PDF",
                    data=bytes(pdf_bytes),
                    file_name=f"Verified_{cert_id_input}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Помилка в даних дати: {e}")
        else:
            st.error(f"❌ Сертифікат '{cert_id_input}' не знайдено.")
