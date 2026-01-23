import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import time
import base64
from io import BytesIO
from datetime import datetime, timedelta
from fpdf import FPDF

# --- КОНФІГУРАЦІЯ ---
FONT_PATH = "dejavu-sans.book.ttf"
BG_IMAGE = "background.webp"
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# --- СТИЛІ ТА АДАПТИВНІСТЬ ---
def apply_advanced_styling(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 600px, cover;
        background-attachment: fixed;
    }}

    .main-title {{ font-size: clamp(32px, 8vw, 52px); font-weight: 800; color: #1a1a1a !important; text-align: center; margin-top: 5vh; }}
    .sub-title {{ font-size: 16px; color: #333; text-align: center; margin-bottom: 30px; }}

    /* СКЛЯНЕ ПОЛЕ */
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.3) !important;
        backdrop-filter: blur(12px);
        border: 2px solid rgba(255, 255, 255, 0.5) !important;
        border-radius: 16px !important;
        color: #000 !important;
        text-align: center !important;
    }}

    /* АДАПТИВНА КАРТКА */
    .result-card {{
        background: rgba(255, 255, 255, 0.95);
        border-radius: 25px;
        padding: clamp(15px, 5vw, 40px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        display: flex;
        flex-wrap: wrap; /* Дозволяє блокам переноситись */
        gap: 20px;
        justify-content: space-between;
    }}
    
    .card-col {{ flex: 1; min-width: 200px; }} /* Мінімальна ширина для переносу */
    .qr-col {{ width: 140px; text-align: center; margin: 0 auto; }}

    @media (max-width: 768px) {{
        .result-card {{ flex-direction: column; align-items: center; text-align: center; }}
        .card-col {{ width: 100%; }}
    }}

    .label {{ color: #888; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
    .value {{ color: #1a1a1a; font-size: 17px; font-weight: 600; margin-bottom: 12px; }}
    </style>
    """, unsafe_allow_html=True)

# --- ГЕНЕРАЦІЯ PDF ---
def generate_pdf_safe(row, expiry_date, program_name, verify_url):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(FONT_PATH):
        pdf.add_font("DejaVu", "", FONT_PATH)
        pdf.set_font("DejaVu", size=12)
        f_m = "DejaVu"
    else:
        pdf.set_font("Helvetica", size=12)
        f_m = "Helvetica"

    pdf.set_font(f_m, size=22)
    pdf.cell(190, 20, "Підтвердження", ln=True, align='C')
    pdf.set_font(f_m, size=11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(190, 10, f"Сертифікат №{row['id']}", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    table = [
        ("№ сертифікату", row['id']), ("Ім'я власника", row['name']),
        ("Програма", program_name), ("Інструктор", row['instructor']),
        ("Дата видачі", pd.to_datetime(row['date']).strftime('%d.%m.%Y')),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y'))
    ]
    for l, v in table:
        pdf.set_x(25)
        pdf.cell(50, 10, l, border=1)
        pdf.cell(90, 10, str(v), border=1, ln=True, align='C')

    qr = qrcode.make(verify_url)
    qr_b = BytesIO()
    qr.save(qr_b, format="PNG")
    pdf.image(qr_b, x=145, y=pdf.get_y() + 10, w=35)
    return bytes(pdf.output())

# --- ЛОГІКА ---
apply_advanced_styling(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Офіційна база даних верифікації</p>', unsafe_allow_html=True)

# Безпечне очищення вводу
params = st.query_params
raw_id = params.get("cert_id", "")
url_id = re.sub(r'[^a-zA-Z0-9]', '', str(raw_id))

col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    u_input = st.text_input("", value=url_id, placeholder="Номер документа").strip().upper()
    search_btn = st.button("ПЕРЕВІРИТИ")

if search_btn or url_id:
    clean_id = re.sub(r'[^a-zA-Z0-9]', '', u_input if search_btn else url_id)
    
    if not clean_id:
        st.warning("Будь ласка, введіть номер.")
    else:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            
            # Валідація стовпців
            if all(c in df.columns for c in ['id', 'name', 'program', 'instructor', 'date']):
                df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
                match = df[df['id'] == clean_id]

                if not match.empty:
                    row = match.iloc[0]
                    p_id = str(row['program']).split('.')[0].strip()
                    p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
                    d_exp = pd.to_datetime(row['date'], dayfirst=True) + timedelta(days=1095)
                    
                    v_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={clean_id}"
                    
                    # Генерація QR для екрану
                    qr_img = qrcode.make(v_url)
                    buf = BytesIO()
                    qr_img.save(buf, format="PNG")
                    q_b64 = base64.b64encode(buf.getvalue()).decode()

                    st.markdown(f"""
                    <div class="result-card">
                        <div class="card-col">
                            <div class="label">№ СЕРТИФІКАТУ</div><div class="value">{row['id']}</div>
                            <div class="label">ІМ'Я ВЛАСНИКА</div><div class="value">{row['name']}</div>
                            <div class="label">ПРОГРАМА</div><div class="value">{p_name}</div>
                            <div class="label">ІНСТРУКТОР</div><div class="value">{row['instructor']}</div>
                        </div>
                        <div class="card-col">
                            <div class="label">ДАТА ВИДАЧІ</div><div class="value">{pd.to_datetime(row['date']).strftime('%d.%m.%Y')}</div>
                            <div class="label">ДІЙСНИЙ ДО</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                            <div class="label">СТАТУС</div><div class="value" style="color:#2ecc71;">● АКТИВНИЙ</div>
                        </div>
                        <div class="qr-col">
                            <img src="data:image/png;base64,{q_b64}" width="120">
                            <div style="font-size:9px; color:#bbb; margin-top:5px; font-weight:800;">VERIFY QR</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    pdf_b = generate_pdf_safe(row, d_exp, p_name, v_url)
                    st.download_button("📥 ЗАВАНТАЖИТИ ПІДТВЕРДЖЕННЯ (PDF)", pdf_b, f"Verify_{clean_id}.pdf")
                else:
                    time.sleep(1) # Затримка проти підбору номерів
                    st.error("Документ не знайдено.")
            else:
                st.error("Помилка структури бази даних.")
        except Exception:
            st.error("Тимчасова помилка сервісу. Спробуйте пізніше.")
