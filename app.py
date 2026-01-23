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

# --- КОНФІГУРАЦІЯ ТА ШРИФТ ---
FONT_PATH = "dejavu-sans.book.ttf"
BG_IMAGE = "background.webp"

PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# --- СТИЛІ ТА СКЛЯНИЙ ДИЗАЙН ---
def apply_glass_design(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 500px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 500px, cover;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }}

    .main-title {{ font-size: 52px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 40px; }}
    .sub-title {{ font-size: 18px; color: #444; text-align: center; margin-bottom: 40px; opacity: 0.7; }}

    /* СКЛЯНЕ ПОЛЕ ВВЕДЕННЯ (Glassmorphism) */
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 16px !important;
        color: #1a1a1a !important;
        font-size: 22px !important;
        padding: 20px !important;
        text-align: center !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05) !important;
    }}
    .stTextInput > div > div > input:focus {{
        background: rgba(255, 255, 255, 0.6) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
        transform: scale(1.02);
    }}

    /* СКЛЯНА КНОПКА З АНІМАЦІЄЮ */
    div.stButton > button {{
        background: rgba(26, 26, 26, 0.8) !important;
        backdrop-filter: blur(5px);
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 50px !important;
        padding: 12px 60px !important;
        font-weight: 700 !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        width: auto !important;
        display: block; margin: 0 auto;
    }}
    div.stButton > button:hover {{
        background: rgba(0, 0, 0, 1) !important;
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2) !important;
    }}

    /* КАРТКА РЕЗУЛЬТАТУ З АНІМАЦІЄЮ ПОЯВИ */
    .result-card {{
        background: rgba(255, 255, 255, 0.9);
        border-radius: 30px;
        padding: 40px;
        border: 1px solid #eee;
        box-shadow: 0 20px 40px rgba(0,0,0,0.05);
        animation: fadeIn 0.8s ease-out;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .label-text {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
    .value-text {{ color: #1a1a1a; font-size: 19px; font-weight: 600; margin-bottom: 20px; }}
    </style>
    """, unsafe_allow_html=True)

def generate_pdf(row, expiry_date, program_name, verify_url):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(FONT_PATH):
        pdf.add_font("DejaVu", "", FONT_PATH)
        pdf.set_font("DejaVu", size=12)
        f_name = "DejaVu"
    else:
        pdf.set_font("Arial", size=12)
        f_name = "Arial"

    pdf.set_font(f_name, size=24)
    pdf.cell(190, 20, "Підтвердження", ln=True, align='C')
    pdf.ln(10)

    data = [
        ("№ сертифікату", row['id']), ("Ім'я власника", row['name']),
        ("Програма навчання", program_name), ("Інструктор(и)", row['instructor']),
        ("Дата видачі", pd.to_datetime(row['date']).strftime('%d.%m.%Y')),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y'))
    ]
    for l, v in data:
        pdf.cell(65, 12, l, border=1)
        pdf.cell(125, 12, str(v), border=1, ln=True, align='C')

    qr_img = qrcode.make(verify_url)
    qr_img.save("pdf_qr.png")
    pdf.ln(20)
    pdf.image("pdf_qr.png", x=145, y=pdf.get_y(), w=35)
    if os.path.exists("pdf_qr.png"): os.remove("pdf_qr.png")
    return bytes(pdf.output())

# --- ЛОГІКА ---
apply_glass_design(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер вашого документа</p>', unsafe_allow_html=True)

query_params = st.query_params
url_id = re.sub(r'[^a-zA-Z0-9]', '', query_params.get("cert_id", ""))

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    cert_input = st.text_input("", value=url_id, placeholder="Наприклад: A0001").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

if search_btn or url_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
        
        target = re.sub(r'[^a-zA-Z0-9]', '', cert_input if search_btn else url_id)
        match = df[df['id'] == target]

        if not match.empty:
            row = match.iloc[0]
            p_id = str(row['program']).split('.')[0].strip()
            p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
            d_exp = pd.to_datetime(row['date'], dayfirst=True) + timedelta(days=1095)
            
            # QR-код (Змініть домен на свій після деплою)
            verify_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={target}"
            
            qr = qrcode.QRCode(box_size=10, border=1)
            qr.add_data(verify_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img_qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            st.markdown(f"""
            <div class="result-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="width: 70%;">
                        <div class="label-text">Учасник</div><div class="value-text">{row['name']}</div>
                        <div class="label-text">Програма</div><div class="value-text">{p_name}</div>
                        <div class="label-text">Статус</div><div class="value-text" style="color:#2ecc71;">● АКТИВНИЙ</div>
                    </div>
                    <div style="width: 25%; text-align: center; border: 1px solid #eee; padding: 10px; border-radius: 15px;">
                        <img src="data:image/png;base64,{qr_b64}" width="100%">
                        <div style="font-size: 10px; color: #888; margin-top: 5px; font-weight: 700;">SCAN TO VERIFY</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            pdf_bytes = generate_pdf(row, d_exp, p_name, verify_url)
            st.download_button("📥 ЗАВАНТАЖИТИ PDF ПІДТВЕРДЖЕННЯ", pdf_bytes, f"Confirm_{target}.pdf")
        else:
            st.error("Сертифікат не знайдено. Перевірте номер.")
    except Exception as e:
        st.error(f"Помилка підключення: {e}")
