import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import base64
from io import BytesIO
from datetime import datetime, timedelta

# --- КОНФІГУРАЦІЯ ---
BG_IMAGE = "background.webp"
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# --- СТИЛІЗАЦІЯ ---
def apply_style(webp_file):
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
    .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 30px; }}
    .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 30px; opacity: 0.8; }}
    
    div[data-baseweb="input"] {{ background-color: white !important; border: 2.5px solid #1a1a1a !important; border-radius: 16px !important; }}
    input {{ color: #1a1a1a !important; font-size: 20px !important; text-align: center !important; }}
    
    .stButton {{ display: flex; justify-content: center; }}
    .stButton > button {{
        background-color: #1a1a1a !important; color: white !important;
        padding: 15px 80px !important; border-radius: 50px !important;
        font-weight: 800 !important; border: 2.5px solid #1a1a1a !important;
    }}
    
    .result-card {{
        background: #ffffff; width: 100%; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 40px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px;
        color: #1a1a1a !important;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
    .value {{ font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #1a1a1a; }}
    
    .st-green {{ color: #2ecc71 !important; font-weight: 800; }}
    .st-yellow {{ color: #f1c40f !important; font-weight: 800; }}
    .st-red {{ color: #e74c3c !important; font-weight: 800; }}
    
    .social-icon {{ width: 35px; margin: 0 10px; cursor: pointer; transition: 0.3s; }}
    .social-icon:hover {{ opacity: 0.7; }}
    </style>
    """, unsafe_allow_html=True)

# --- ДОДАТОК ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер документа для перевірки в офіційній базі</p>', unsafe_allow_html=True)

# Обробка ID (URL або Ввід)
query_params = st.query_params
default_id = query_params.get("cert_id", "")
if isinstance(default_id, list): default_id = default_id[0]
default_id = re.sub(r'[^a-zA-Z0-9]', '', str(default_id)).upper()

_, col_in, _ = st.columns([1, 2, 1])
with col_in:
    cert_input = st.text_input("ID", value=default_id, label_visibility="collapsed", placeholder="ВВЕДІТЬ НОМЕР...").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

final_id = cert_input if cert_input else default_id

if final_id:
    try:
        # Підключення до Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
        
        match = df[df['id'] == final_id]

        if not match.empty:
            row = match.iloc[0]
            p_id = str(row['program']).split('.')[0].strip()
            p_name = PROGRAMS.get(p_id, f"Спецкурс №{p_id}")
            
            # Розрахунок термінів
            # Переконайтеся, що в таблиці дата у форматі ДД.ММ.РРРР
            d_iss = pd.to_datetime(row['date'], dayfirst=True)
            d_exp = d_iss + timedelta(days=1095)
            days_left = (d_exp - datetime.now()).days

            if days_left < 0:
                cls, txt = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
            elif days_left <= 30:
                cls, txt = "st-yellow", "ПІДХОДИТЬ ДО КІНЦЯ"
            else:
                cls, txt = "st-green", "АКТИВНИЙ"

            # Генерація QR Коду
            share_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={final_id}"
            qr = qrcode.make(share_url)
            buf = BytesIO()
            qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            # ВІЗУАЛЬНИЙ ВИВІД (Один блок для уникнення помилок відображення)
            st.markdown(f"""
            <div class="result-card">
                <div>
                    <div class="label">Учасник тренінгу</div>
                    <div class="value">{row['name']}</div>
                    <div class="label">Програма навчання</div>
                    <div class="value">{p_name}</div>
                    <div class="label">Інструктор</div>
                    <div class="value">{row['instructor']}</div>
                </div>
                <div>
                    <div class="label">Дата видачі</div>
                    <div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                    <div class="label">Дійсний до</div>
                    <div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                    <div class="label">Залишилось днів</div>
                    <div class="value {cls}">{max(0, days_left)}</div>
                </div>
                
                <div style="grid-column: span 2; border-top: 1px solid #eee; padding-top: 30px; display: flex; justify-content: space-between; align-items: center;">
                    <div class="{cls}" style="font-size: 20px; display: flex; align-items: center;">
                        <span style="margin-right: 10px;">●</span> {txt}
                    </div>
                    <img src="data:image/png;base64,{qr_b64}" width="100" style="border: 1px solid #eee; border-radius: 10px; padding: 5px;">
                </div>
            </div>

            <div style="text-align: center; margin-top: 25px;">
                <p style="color:#888; font-weight:bold; font-size:12px; margin-bottom:15px; text-transform: uppercase; letter-spacing: 1px;">Поділитися результатом</p>
                <div style="display: flex; justify-content: center; align-items: center;">
                    <a href="https://t.me/share/url?url={share_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" class="social-icon">
                    </a>
                    <a href="viber://forward?text={share_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/3670/3670059.png" class="social-icon">
                    </a>
                    <a href="https://api.whatsapp.com/send?text={share_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" class="social-icon">
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.error(f"Сертифікат №{final_id} не знайдено в базі даних. Перевірте правильність вводу.")
            
    except Exception as e:
        st.error(f"Критична помилка додатка: {e}")
        st.info("Перевірте структуру Google-таблиці та налаштування Secrets.")
