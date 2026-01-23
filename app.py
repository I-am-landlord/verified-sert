import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import time
import base64
import urllib.parse
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

    .main-title {{ font-size: 42px; font-weight: 800; color: #000000 !important; text-align: center; margin-top: 50px; }}
    .sub-title {{ font-size: 18px; color: #000000 !important; text-align: center; margin-bottom: 30px; opacity: 0.8; }}

    /* ФІКС: БІЛЕ ПОЛЕ З ЧОРНОЮ РАМКОЮ */
    .stTextInput > div > div {{
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
    }}
    .stTextInput > div > div > input {{
        color: #000000 !important;
        background-color: #FFFFFF !important;
        font-size: 20px !important;
        text-align: center !important;
    }}

    /* Кнопка */
    div.stButton > button {{
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 50px !important;
        padding: 10px 50px !important;
        border: none !important;
        margin: 0 auto; display: block;
    }}

    /* Картка результату */
    .result-card {{
        background: #FFFFFF !important;
        border: 2px solid #000000;
        border-radius: 20px;
        padding: 30px;
        color: #000000 !important;
        box-shadow: 10px 10px 0px #000000;
    }}
    .label-text {{ color: #666666 !important; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .value-text {{ color: #000000 !important; font-size: 18px; font-weight: 600; margin-bottom: 12px; }}

    /* Іконки соцмереж */
    .social-icon {{
        width: 40px;
        height: 40px;
        margin: 0 10px;
        transition: 0.3s;
    }}
    .social-icon:hover {{ transform: scale(1.1); }}
    
    .promo-box {{
        background: #f0fff0;
        border: 2px dashed #000;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-top: 20px;
        color: #000 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- ЛОГІКА РЕКЛАМИ ---
def get_promo(p_id, is_expired):
    if is_expired:
        return {"t": "Поновіть сертифікат", "d": "Ваш документ прострочений. Запишіться на курс для оновлення!", "l": "#"}
    if p_id in ["1", "2"]:
        return {"t": "Курс для тварин", "d": "Вмієте допомагати людям? Навчіться рятувати і чотирилапих!", "l": "#"}
    if p_id == "4":
        return {"t": "Допомога людям", "d": "Тепер час опанувати навички домедичної допомоги для людей!", "l": "#"}
    return {"t": "Інші тренінги", "d": "Перегляньте наш повний каталог навчальних програм.", "l": "#"}

# --- ПРОГРАМА ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Сервіс для верифікації сертифікатів</p>', unsafe_allow_html=True)

params = st.query_params
url_id = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))

_, col_m, _ = st.columns([1, 2, 1])
with col_m:
    u_input = st.text_input("", value=url_id, placeholder="Номер сертифікату").strip().upper()
    if st.button("ЗНАЙТИ"):
        url_id = u_input

if url_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
        
        match = df[df['id'] == url_id]

        if not match.empty:
            row = match.iloc[0]
            p_id = str(row['program']).split('.')[0].strip()
            p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
            d_exp = pd.to_datetime(row['date'], dayfirst=True) + timedelta(days=1095)
            is_expired = (d_exp < datetime.now())

            qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={url_id}")
            buf = BytesIO()
            qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            st.markdown(f"""
            <div class="result-card">
                <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
                    <div style="flex: 2; min-width: 250px;">
                        <div class="label-text">ПІБ Учасника</div><div class="value-text">{row['name']}</div>
                        <div class="label-text">Курс</div><div class="value-text">{p_name}</div>
                        <div class="label-text">Інструктор</div><div class="value-text">{row['instructor']}</div>
                        <div class="label-text">Дійсний до</div><div class="value-text">{d_exp.strftime('%d.%m.%Y')}</div>
                        <div class="label-text">Статус</div>
                        <div class="value-text" style="color:{'red' if is_expired else 'green'} !important;">
                            ● {'ПРОСТРОЧЕНИЙ' if is_expired else 'ДІЙСНИЙ'}
                        </div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <img src="data:image/png;base64,{qr_b64}" width="140">
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Реклама
            pr = get_promo(p_id, is_expired)
            st.markdown(f"""
            <div class="promo-box">
                <h4 style="margin:0;">{pr['t']}</h4>
                <p style="font-size:14px; margin:10px 0;">{pr['d']}</p>
                <a href="{pr['l']}" style="color:black; font-weight:bold;">ДЕТАЛЬНІШЕ →</a>
            </div>
            """, unsafe_allow_html=True)

            # Соцмережі іконками
            share_url = f"https://verify.streamlit.app/?cert_id={url_id}"
            st.markdown(f"""
            <div style="text-align: center; margin-top: 25px;">
                <p style="font-size:12px; font-weight:bold; color:black;">ПОДІЛИТИСЯ:</p>
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
            """, unsafe_allow_html=True)
        else:
            st.error("Сертифікат не знайдено. Зазвичай сертифікати додаються до бази даних протягом 14 днів з дати проходження тренінгу.")
    except:
        st.error("Помилка бази даних.")
