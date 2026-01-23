import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- СЛОВНИК ПРОГРАМ ---
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

# --- НАЛАШТУВАННЯ СТИЛЮ (CSS) ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    
    .main {
        background: linear-gradient(135deg, #e0f7fa 0%, #f3e5f5 100%);
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        border-radius: 50px;
        border: 1px solid #000;
        background-color: transparent;
        color: #000;
        padding: 10px 25px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #000;
        color: #fff;
    }
    .hero-text {
        font-size: 42px;
        font-weight: 700;
        color: #333;
        margin-bottom: 5px;
    }
    .highlight {
        color: #0097a7;
    }
    .sub-text {
        font-size: 18px;
        color: #555;
        margin-bottom: 30px;
    }
    .card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ФУНКЦІЯ ГЕНЕРАЦІЇ PDF ---
def create_pdf(data, status, expiry_date, program_name):
    pdf = FPDF()
    pdf.add_page()
    
    font_filename = "DejaVuSans.ttf" 
    if os.path.exists(font_filename):
        pdf.add_font("DejaVu", style="", fname=font_filename)
        pdf.add_font("DejaVu", style="B", fname=font_filename) # Для простоти той самий файл
        pdf.set_font("DejaVu", size=12)
        font_name = "DejaVu"
    else:
        pdf.set_font("Helvetica", size=12)
        font_name = "Helvetica"

    # Дизайн бланку
    pdf.set_draw_color(0, 151, 167)
    pdf.set_line_width(1)
    pdf.rect(10, 10, 190, 277)
    
    pdf.ln(20)
    pdf.set_font(font_name, size=24)
    pdf.set_text_color(0, 151, 167)
    pdf.cell(190, 15, text="ПІДТВЕРДЖЕННЯ ТРЕНІНГУ", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_text_color(50, 50, 50)
    
    def add_field(label, value):
        pdf.set_font(font_name, size=11)
        pdf.set_x(25)
        pdf.cell(60, 10, text=f"{label}:", ln=False)
        pdf.set_font(font_name, size=12)
        pdf.cell(100, 10, text=str(value), ln=True)

    add_field("Сертифікат №", data['id'])
    add_field("Учасник", data['name'])
    add_field("Програма", program_name)
    add_field("Інструктор(и)", data['instructor'])
    add_field("Дата видачі", data['date'])
    add_field("Статус дії", status)

    # QR-код
    qr_text = f"Cert:{data['id']} | {data['name']} | {program_name}"
    qr = qrcode.make(qr_text)
    qr.save("temp_qr.png")
    pdf.image("temp_qr.png", x=150, y=240, w=35)
    
    if os.path.exists("temp_qr.png"): os.remove("temp_qr.png")
    return pdf.output()

# --- ДОДАТОК ---
local_css()

# Заголовок у стилі картинки
st.markdown('<p class="hero-text">Знання, що <span class="highlight">рятують життя</span></p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Перевірте дійсність вашого сертифікату у зручному форматі</p>', unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=300)
    df.columns = df.columns.str.strip().str.lower()
    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
except Exception as e:
    st.error("Помилка зв'язку з базою даних.")
    st.stop()

# Поле пошуку
cert_id_input = st.text_input("Введіть номер сертифікату:").strip().upper()

if st.button("ПЕРЕВІРИТИ →"):
    if cert_id_input:
        match = df[df['id'] == cert_id_input]
        
        if not match.empty:
            res = match.iloc[0].to_dict()
            
            # Обробка програми
            prog_code = str(res.get('program', '1')).strip()
            prog_name = PROGRAMS.get(prog_code, "Спеціалізований тренінг")
            
            # Обробка дати
            try:
                date_obj = pd.to_datetime(res['date'], dayfirst=True).to_pydatetime()
                expiry_date = date_obj + timedelta(days=3*365)
                days_left = (expiry_date - datetime.now()).days
                
                status = "АКТИВНИЙ" if days_left > 0 else "ТЕРМІН ДІЇ ВИЙШОВ"
                
                # Картка результату
                st.markdown(f"""
                <div class="card">
                    <h3 style="color:#0097a7; margin-top:0;">📋 Результат знайдено</h3>
                    <p><b>Учасник:</b> {res['name']}</p>
                    <p><b>Програма:</b> {prog_name}</p>
                    <p><b>Інструктор(и):</b> {res['instructor']}</p>
                    <p><b>Дійсний до:</b> {expiry_date.strftime('%d.%m.%Y')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if days_left <= 30 and days_left > 0:
                    st.warning(f"⚠️ Термін дії закінчується через {days_left} дн. Рекомендуємо оновити знання!")

                pdf_bytes = create_pdf(res, status, expiry_date, prog_name)
                st.download_button("Завантажити підтвердження (PDF)", bytes(pdf_bytes), f"Cert_{cert_id_input}.pdf")
                
            except Exception as e:
                st.error("Помилка формату дати в таблиці.")
        else:
            st.error("Сертифікат не знайдено.")
