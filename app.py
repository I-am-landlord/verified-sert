import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import re
import base64
import os
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

def clean_id(text):
    if text is None: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()

# --- СТИЛІ (ВАШ ДИЗАЙН) ---
def apply_custom_styles(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 600px, cover; background-attachment: fixed;
    }}
    .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 40px; }}
    .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 30px; opacity: 0.8; }}
    
    /* Картка результату */
    .result-card {{
        background: #ffffff; width: 100%; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 45px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 40px;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; }}
    .value {{ color: #1a1a1a; font-size: 19px; font-weight: 600; margin-bottom: 25px; }}
    
    /* Статуси */
    .active-status {{ color: #2ecc71 !important; font-weight: 800; }}
    .warning-status {{ color: #f1c40f !important; font-weight: 800; }}
    .expired-status {{ color: #e74c3c !important; font-weight: 800; }}

    /* Реклама */
    .promo-card {{
        grid-column: span 2; position: relative; height: 180px; border-radius: 20px;
        overflow: hidden; border: 1.5px solid #1a1a1a;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.2) grayscale(1); transition: 0.6s ease;
    }}
    .promo-card:hover .promo-bg {{ filter: brightness(0.8) grayscale(0); }}
    .promo-content {{ position: relative; z-index: 2; color: white; text-align: center; padding: 45px 20px; }}
    
    /* Пошук */
    div[data-baseweb="input"] {{
        background-color: white !important; border: 2.5px solid #1a1a1a !important; border-radius: 16px !important;
    }}
    .stButton > button {{
        background: #1a1a1a !important; color: white !important; padding: 10px 80px !important; border-radius: 50px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Офіційна база даних документів</p>', unsafe_allow_html=True)

# Отримання ID
query_params = st.query_params
url_id = query_params.get("cert_id", "")
if isinstance(url_id, list): url_id = url_id[0]
url_id = clean_id(url_id)

_, col_search, _ = st.columns([1, 2, 1])
with col_search:
    # ВИПРАВЛЕНО: label тепер не пустий
    user_input = st.text_input("Введіть ID", value=url_id, placeholder="Номер сертифікату", label_visibility="collapsed").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

target_id = clean_id(user_input if search_btn else url_id)

if target_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        
        # Захист від порожньої таблиці
        if df is not None and not df.empty:
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().upper()
            
            match = df[df['id'] == target_id]

            if not match.empty:
                row = match.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                
                # Логіка дат
                d_iss = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = d_iss + timedelta(days=1095)
                days_left = (d_exp - datetime.now()).days

                if days_left < 0:
                    cls, txt = "expired-status", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
                elif days_left <= 30:
                    cls, txt = "warning-status", "ПІДХОДИТЬ ДО КІНЦЯ"
                else:
                    cls, txt = "active-status", "АКТИВНИЙ"

                # QR
                qr = qrcode.make(f"https://verify.streamlit.app/?cert_id={target_id}")
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                # Реклама
                p_img = "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800"
                p_title = "ПЕРША ДОПОМОГА ТВАРИНАМ"

                # КАРТКА
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <div class="label">Учасник тренінгу</div><div class="value">{row['name']}</div>
                        <div class="label">Програма навчання</div><div class="value">{PROGRAMS.get(p_id, 'Курс першої допомоги')}</div>
                        <div class="label">Інструктор</div><div class="value">{row.get('instructor', 'Інструктор Центру')}</div>
                    </div>
                    <div>
                        <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                        <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                        <div class="label">Залишилось днів</div><div class="value {cls}">{max(0, days_left)}</div>
                    </div>
                    <div class="promo-card">
                        <div class="promo-bg" style="background-image: url('{p_img}');"></div>
                        <div class="promo-content">
                            <div style="font-weight:800; font-size:20px;">{p_title}</div>
                            <div style="font-size:13px;">Отримайте знижку 15% як випускник</div>
                        </div>
                    </div>
                    <div style="grid-column: span 2; border-top: 1px solid #eee; padding-top: 25px; display: flex; justify-content: space-between; align-items: center;">
                        <div class="{cls}" style="font-size: 18px;">● СТАТУС: {txt}</div>
                        <img src="data:image/png;base64,{qr_b64}" width="90">
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Документ {target_id} не знайдено.")
    except Exception as e:
        st.error("Системна помилка. Перевірте з'єднання з таблицею.")
