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
# Приклади фото для реклами (можна замінити на власні локальні файли)
PROMO_IMAGES = {
    "human": "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?q=80&w=1000", 
    "pets": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?q=80&w=1000",
    "general": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=1000"
}

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

    .main-title {{ font-size: 42px; font-weight: 800; color: #000 !important; text-align: center; margin-top: 30px; }}
    .sub-title {{ font-size: 18px; color: #000 !important; text-align: center; margin-bottom: 30px; opacity: 0.8; }}

    /* Центрування кнопки та поля */
    .stTextInput {{ width: 100% !important; }}
    div.stButton {{ text-align: center; }}
    
    .stTextInput > div > div {{
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
    }}
    .stTextInput > div > div > input {{
        color: #000000 !important;
        background-color: #FFFFFF !important;
        font-size: 18px !important;
        text-align: center !important;
    }}

    div.stButton > button {{
        background-color: #000 !important;
        color: #fff !important;
        border-radius: 50px !important;
        padding: 12px 60px !important;
        border: none !important;
        font-weight: 700 !important;
        transition: 0.3s;
    }}

    /* Картка результату */
    .result-card {{
        background: #FFFFFF !important;
        border: 2px solid #000;
        border-radius: 20px;
        padding: 30px;
        color: #000 !important;
        margin-top: 20px;
    }}

    /* Рекламний блок з ефектом проявлення */
    .promo-card {{
        position: relative;
        width: 100%;
        height: 200px;
        border-radius: 20px;
        overflow: hidden;
        margin-top: 20px;
        border: 2px solid #000;
        cursor: pointer;
    }}
    .promo-bg {{
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover;
        background-position: center;
        filter: brightness(0.3) grayscale(0.5);
        transition: 0.6s ease;
    }}
    .promo-card:hover .promo-bg {{
        filter: brightness(1) grayscale(0);
        transform: scale(1.05);
    }}
    .promo-content {{
        position: relative;
        z-index: 2;
        color: white;
        text-align: center;
        padding: 40px 20px;
        text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
    }}

    .social-icon {{ width: 35px; margin: 0 10px; transition: 0.3s; }}
    .social-icon:hover {{ transform: translateY(-3px); }}
    </style>
    """, unsafe_allow_html=True)

# --- ЛОГІКА РЕКЛАМИ ---
def get_promo(p_id, is_expired):
    if is_expired:
        return {"t": "ПОНОВЛЕННЯ ЗНАНЬ", "d": "Ваш сертифікат недійсний. Варто оновити знання!", "l": "#", "img": PROMO_IMAGES['general']}
    if p_id in ["1", "2"]:
        return {"t": "ПЕРША ДОПОМОГА ТВАРИНАМ", "d": "Подбайте про чотирилапих друзів. Запишіться на тренінг Перша допомога домашнім тваринам!", "l": "#", "img": PROMO_IMAGES['pets']}
    if p_id == "4":
        return {"t": "ДОПОМОГА ЛЮДЯМ", "d": "Навчіться рятувати людські життя на базовому тренінгу!", "l": "#", "img": PROMO_IMAGES['human']}
    return {"t": "НАШ КАТАЛОГ", "d": "Перегляньте всі доступні навчальні програми.", "l": "#", "img": PROMO_IMAGES['general']}

# --- ОСНОВНА ЛОГІКА ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Сервіс для верифікації сертифікатів</p>', unsafe_allow_html=True)

params = st.query_params
url_id = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))

_, col_m, _ = st.columns([1, 1.5, 1])
with col_m:
    u_input = st.text_input("", value=url_id, placeholder="Номер сертифікату").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

if search_btn or url_id:
    curr_id = u_input if search_btn else url_id
    if curr_id:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            match = df[df['id'] == curr_id]

            if not match.empty:
                row = match.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Програма №{p_id}")
                
                # ЛОГІКА КОЛЬОРІВ СТАТУСУ
                date_obj = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = date_obj + timedelta(days=1095)
                days_left = (d_exp - datetime.now()).days
                
                if days_left < 0:
                    status_color, status_text = "red", "ТЕРМІН ДІЇ ЗАВЕРШИВСЯ"
                    is_expired = True
                elif days_left <= 30:
                    status_color, status_text = "orange", f"ЗАВЕРШУЄТЬСЯ (залишилось {days_left} дн.)"
                    is_expired = False
                else:
                    status_color, status_text = "green", "ДІЙСНИЙ"
                    is_expired = False

                qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={curr_id}")
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
                        <div style="flex: 2; min-width: 250px;">
                            <div style="color:#666; font-size:12px; font-weight:700;">УЧАСНИК</div>
                            <div style="font-size:20px; font-weight:600; margin-bottom:15px;">{row['name']}</div>
                            <div style="color:#666; font-size:12px; font-weight:700;">КУРС</div>
                            <div style="font-size:16px; font-weight:600; margin-bottom:15px;">{p_name}</div>
                            <div style="color:#666; font-size:12px; font-weight:700;">СТАТУС</div>
                            <div style="font-size:18px; font-weight:800; color:{status_color} !important;">● {status_text}</div>
                        </div>
                        <div style="flex: 1; text-align: center;">
                            <img src="data:image/png;base64,{qr_b64}" width="130">
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Рекламний блок з "проявленням"
                pr = get_promo(p_id, is_expired)
                st.markdown(f"""
                <a href="{pr['l']}" style="text-decoration:none;">
                    <div class="promo-card">
                        <div class="promo-bg" style="background-image: url('{pr['img']}');"></div>
                        <div class="promo-content">
                            <h3 style="margin:0; font-size:22px;">{pr['t']}</h3>
                            <p style="margin:10px 0; font-size:14px; opacity:0.9;">{pr['d']}</p>
                            <span style="border: 1px solid white; padding: 5px 15px; border-radius: 20px; font-size:12px;">ДЕТАЛЬНІШЕ</span>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

                # Соцмережі
                s_url = f"https://verify.streamlit.app/?cert_id={curr_id}"
                st.markdown(f"""
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://t.me/share/url?url={s_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" class="social-icon">
                    </a>
                    <a href="viber://forward?text={s_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/3670/3670059.png" class="social-icon">
                    </a>
                    <a href="https://api.whatsapp.com/send?text={s_url}" target="_blank">
                        <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" class="social-icon">
                    </a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Сертифікат не знайдено.")
        except:
            st.error("Помилка бази даних.")
