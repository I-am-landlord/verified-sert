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

# --- ПОКРАЩЕНИЙ ДИЗАЙН (CSS) ---
def local_css():
    st.markdown("""
    <style>
    /* Головний фон та шрифти */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5fafd 0%, #ffffff 100%);
    }
    
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 48px;
        font-weight: 800;
        color: #1a1a1a;
        margin-bottom: 0px;
    }
    
    .highlight {
        color: #26a69a; /* Колір "рятують життя" */
    }
    
    .sub-title {
        color: #666;
        font-size: 18px;
        margin-bottom: 40px;
    }

    /* Стилізація поля вводу */
    .stTextInput input {
        border-radius: 12px !important;
        border: 1px solid #ddd !important;
        padding: 12px !important;
        background-color: white !important;
        color: black !important;
    }

    /* Стилізація кнопки (овальна як на макеті) */
    div.stButton > button {
        border-radius: 30px !important;
        border: 1.5px solid #1a1a1a !important;
        background-color: transparent !important;
        color: #1a1a1a !important;
        padding: 8px 35px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #1a1a1a !important;
        color: white !important;
    }

    /* Картка результату */
    .result-card {
        background-color: white;
        padding: 40px;
        border-radius: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-top: 30px;
    }
    
    .result-header {
        display: flex;
        align-items: center;
        gap: 15px;
        font-size: 28px;
        font-weight: 700;
        color: #26a69a;
        margin-bottom: 25px;
    }

    .info-label {
        color: #888;
        font-size: 14px;
        margin-bottom: 2px;
    }
    
    .info-value {
        color: #1a1a1a;
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ГЕНЕРАЦІЯ PDF ---
def create_pdf(data, status, expiry_date, program_name):
    pdf = FPDF()
    pdf.add_page()
    
    font_path = "DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", style="", fname=font_path)
        pdf.set_font("DejaVu", size=12)
        font = "DejaVu"
    else:
        pdf.set_font("Helvetica", size=12)
        font = "Helvetica"

    # Естетична рамка
    pdf.set_draw_color(38, 166, 154)
    pdf.set_line_width(0.5)
    pdf.rect(10, 10, 190, 277)

    pdf.ln(25)
    pdf.set_font(font, size=24)
    pdf.set_text_color(38, 166, 154)
    pdf.cell(190, 10, "ПІДТВЕРДЖЕННЯ СЕРТИФІКАТУ", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_text_color(30, 30, 30)
    
    fields = [
        ("№ Сертифікату", data['id']),
        ("Учасник", data['name']),
        ("Програма", program_name),
        ("Інструктори", data['instructor']),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y')),
        ("Статус", status)
    ]

    for label, val in fields:
        pdf.set_font(font, size=11)
        pdf.set_x(30)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(60, 10, f"{label}:")
        pdf.set_font(font, size=12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, str(val), ln=True)

    # QR код
    qr_text = f"https://your-app-url.streamlit.app/?id={data['id']}"
    qr = qrcode.make(qr_text)
    qr.save("qr_temp.png")
    pdf.image("qr_temp.png", x=150, y=240, w=35)
    
    if os.path.exists("qr_temp.png"): os.remove("qr_temp.png")
    return pdf.output()

# --- ЛОГІКА ДОДАТКА ---
local_css()

# Шапка сайту
st.markdown('<h1 class="main-title">Знання, що <span class="highlight">рятують життя</span></h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Перевірте дійсність вашого сертифікату у зручному форматі</p>', unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=300)
    df.columns = df.columns.str.strip().str.lower()
    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
except:
    st.error("Помилка підключення до реєстру.")
    st.stop()

# Центрування контенту через колонки
col_left, col_mid, col_right = st.columns([1, 2, 1])

with col_mid:
    cert_id = st.text_input("Введіть номер сертифікату:", placeholder="Наприклад: 2105").strip().upper()
    check_button = st.button("ПЕРЕВІРИТИ →")

    if check_button and cert_id:
        match = df[df['id'] == cert_id]
        
        if not match.empty:
            row = match.iloc[0].to_dict()
            
            # Обробка даних
            prog_name = PROGRAMS.get(str(row.get('program')), "Курс першої допомоги")
            date_val = pd.to_datetime(row['date'], dayfirst=True)
            expiry_date = date_val + timedelta(days=3*365)
            status = "АКТИВНИЙ" if expiry_date > datetime.now() else "НЕ ДІЙСНИЙ"
            
            # Відмальовка картки результату (HTML)
            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <span>📋</span> Результат знайдено
                </div>
                <div class="info-label">Учасник:</div>
                <div class="info-value">{row['name']}</div>
                
                <div class="info-label">Програма навчання:</div>
                <div class="info-value">{prog_name}</div>
                
                <div class="info-label">Інструктор(и):</div>
                <div class="info-value">{row['instructor']}</div>
                
                <div class="info-label">Дійсний до:</div>
                <div class="info-value">{expiry_date.strftime('%d.%m.%Y')}</div>
                
                <div style="color: {'#26a69a' if status == 'АКТИВНИЙ' else '#e57373'}; font-weight: 700;">
                    ● Статус: {status}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Кнопка завантаження PDF
            pdf_out = create_pdf(row, status, expiry_date, prog_name)
            st.download_button(
                label="ЗАВАНТАЖИТИ PDF ПІДТВЕРДЖЕННЯ",
                data=bytes(pdf_out),
                file_name=f"Certificate_{cert_id}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Сертифікат з таким номером не знайдено в базі даних.")
