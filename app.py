import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
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

# --- ФУНКЦІЯ БЕЗПЕКИ ---
def clean_id(text):
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()

# --- СТИЛІЗАЦІЯ (ПОВНИЙ ПОВРОТ ДО ВАШОГО ДИЗАЙНУ) ---
def apply_custom_styles(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    body, html {{ font-family: 'Inter', sans-serif; }}
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 600px, cover; background-attachment: fixed;
    }}

    .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 40px; }}
    .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 30px; opacity: 0.8; }}

    /* Пошукова секція */
    div[data-baseweb="input"] {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border: 2.5px solid #1a1a1a !important;
        border-radius: 16px !important;
        min-height: 65px;
    }}
    input {{ font-size: 22px !important; text-align: center !important; color: #1a1a1a !important; }}

    .stButton {{ display: flex; justify-content: center; }}
    .stButton > button {{
        background: #1a1a1a !important; color: #fff !important;
        padding: 15px 80px !important; border-radius: 50px !important;
        font-weight: 800 !important; font-size: 16px !important;
        text-transform: uppercase; border: 2.5px solid #1a1a1a !important;
    }}

    /* Картка результату */
    .result-card {{
        background: #ffffff; width: 100%; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 45px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 40px;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; }}
    .value {{ color: #1a1a1a; font-size: 19px; font-weight: 600; margin-bottom: 25px; }}
    
    /* Кольорова індикація */
    .active-status {{ color: #2ecc71 !important; font-weight: 800; }}
    .warning-status {{ color: #f1c40f !important; font-weight: 800; }}
    .expired-status {{ color: #e74c3c !important; font-weight: 800; }}

    /* Реклама з ефектом проявлення */
    .promo-card {{
        grid-column: span 2; position: relative; height: 180px; border-radius: 20px;
        overflow: hidden; border: 1.5px solid #1a1a1a; margin-top: 10px;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.2) grayscale(1); transition: 0.6s ease;
    }}
    .promo-card:hover .promo-bg {{ filter: brightness(0.8) grayscale(0); }}
    .promo-content {{ position: relative; z-index: 2; color: white; text-align: center; padding: 45px 20px; }}

    .social-icon {{ width: 35px; margin: 0 10px; }}
    </style>
    """, unsafe_allow_html=True)

import os
apply_custom_styles(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Офіційна база даних документів</p>', unsafe_allow_html=True)

# Пошук
query_params = st.query_params
url_id = clean_id(query_params.get("cert_id", [""])[0])

_, col_search, _ = st.columns([1, 2, 1])
with col_search:
    user_input = st.text_input("", value=url_id, placeholder="Номер сертифікату", label_visibility="collapsed").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

# Логіка обробки
target_id = clean_id(user_input if search_btn else url_id)

if target_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 допоможе побачити зміни в таблиці миттєво для тестів
        df = conn.read(ttl=0) 
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().upper()
        
        match = df[df['id'] == target_id]

        if not match.empty:
            row = match.iloc[0]
            p_id = str(row['program']).split('.')[0].strip()
            
            # Розрахунок термінів
            d_iss = pd.to_datetime(row['date'], dayfirst=True)
            d_exp = d_iss + timedelta(days=1095)
            days_left = (d_exp - datetime.now()).days

            # Кольори
            if days_left < 0:
                cls, txt = "expired-status", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
            elif days_left <= 30:
                cls, txt = "warning-status", "ПІДХОДИТЬ ДО КІНЦЯ"
            else:
                cls, txt = "active-status", "АКТИВНИЙ"

            # Реклама
            p_img = "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800" if p_id != "4" else "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?w=800"
            p_title = "ПЕРША ДОПОМОГА ТВАРИНАМ" if p_id != "4" else "ДОПОМОГА ЛЮДЯМ (LEVEL 1)"

            # QR
            qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={target_id}")
            buf = BytesIO()
            qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            # ВІДОБРАЖЕННЯ
            st.markdown(f"""
            <div class="result-card">
                <div>
                    <div class="label">Учасник тренінгу</div><div class="value">{row['name']}</div>
                    <div class="label">Програма навчання</div><div class="value">{PROGRAMS.get(p_id, 'Спеціалізований курс')}</div>
                    <div class="label">Інструктор(и)</div><div class="value">{row.get('instructor', 'Офіційний інструктор')}</div>
                </div>
                <div>
                    <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                    <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                    <div class="label">Залишилось днів дії</div><div class="value {cls}">{max(0, days_left)} днів</div>
                </div>
                
                <div class="promo-card">
                    <div class="promo-bg" style="background-image: url('{p_img}');"></div>
                    <div class="promo-content">
                        <div style="font-weight:800; font-size:22px;">{p_title}</div>
                        <div style="font-size:14px; opacity:0.9;">Отримайте нові навички зі знижкою 15% за вашим ID</div>
                    </div>
                </div>

                <div style="grid-column: span 2; border-top: 1px solid #f0f0f0; padding-top: 25px; display: flex; justify-content: space-between; align-items: center;">
                    <div class="{cls}" style="font-size: 20px;">● СТАТУС: {txt}</div>
                    <img src="data:image/png;base64,{qr_b64}" width="100">
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Соцмережі
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <a href="https://t.me/share/url?url=https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={target_id}" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" class="social-icon"></a>
                <a href="viber://forward?text=https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={target_id}" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/3670/3670059.png" class="social-icon"></a>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.error(f"Сертифікат {target_id} не знайдено.")
    except Exception as e:
        st.error("Помилка доступу до даних. Перевірте назви колонок у таблиці (ID, Name, Date, Program, Instructor).")
