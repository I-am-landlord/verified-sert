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

# --- СТИЛІЗАЦІЯ (GLASSMORPHISM + FIX COLORS) ---
def apply_style(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    /* Фон всього додатка */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 600px, cover;
        background-attachment: fixed;
    }}

    .main-title {{ font-size: clamp(32px, 7vw, 52px); font-weight: 800; color: #1a1a1a !important; text-align: center; margin-top: 50px; }}
    .sub-title {{ font-size: 18px; color: #333 !important; text-align: center; margin-bottom: 40px; }}

    /* ВИПРАВЛЕНО: Чисто біле скляне поле введення з чорним текстом */
    div[data-baseweb="input"] {{
        background-color: transparent !important;
    }}
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.6) !important; /* Більш насичений білий для контрасту */
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border: 2px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 16px !important;
        color: #000000 !important; /* ЧОРНИЙ ТЕКСТ */
        font-size: 20px !important;
        padding: 15px !important;
        text-align: center !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1) !important;
    }}
    
    /* Колір плейсхолдера */
    .stTextInput > div > div > input::placeholder {{
        color: rgba(0, 0, 0, 0.4) !important;
    }}

    /* Кнопка пошуку */
    div.stButton > button {{
        background-color: #1a1a1a !important;
        color: white !important;
        border-radius: 50px !important;
        padding: 12px 60px !important;
        border: none !important;
        font-weight: 700 !important;
        margin: 0 auto; display: block;
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: #000000 !important;
        transform: scale(1.02);
    }}

    /* КАРТКА РЕЗУЛЬТАТУ: Чорний текст на білому склі */
    .result-card {{
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 30px;
        padding: 40px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        color: #1a1a1a !important; /* ГАРАНТОВАНИЙ ЧОРНИЙ ТЕКСТ */
    }}
    
    .label-text {{ color: #666 !important; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }}
    .value-text {{ color: #1a1a1a !important; font-size: 18px; font-weight: 600; margin-bottom: 15px; }}

    /* Рекламний блок */
    .promo-banner {{
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
        border: 2px dashed #2ecc71;
        border-radius: 20px;
        padding: 25px;
        margin-top: 30px;
        text-align: center;
    }}
    
    /* Соцмережі */
    .share-btn {{ 
        display: inline-flex; align-items: center; justify-content: center; 
        padding: 10px 18px; margin: 5px; border-radius: 12px; 
        color: white !important; text-decoration: none !important; font-weight: 600; 
    }}
    .tg {{ background-color: #0088cc; }} .vb {{ background-color: #7360f2; }}
    </style>
    """, unsafe_allow_html=True)

# --- ЛОГІКА РЕКЛАМИ ---
def get_promo_data(p_id, is_expired):
    if is_expired:
        return {"title": "🔄 Термін дії вийшов", "desc": "Запишіться на повторний тренінг зі знижкою!", "link": "#"}
    if p_id in ["1", "2"]:
        return {"title": "🐾 Для чотирилапих", "desc": "Ви рятуєте людей, а як щодо тварин? Пройдіть наш спецкурс!", "link": "#"}
    elif p_id == "4":
        return {"title": "👤 Допомога людям", "desc": "Опануйте навички домедичної допомоги для людей!", "link": "#"}
    elif p_id == "3":
        return {"title": "🌟 Розширюйте навички", "desc": "Ознайомтесь з іншими нашими програмами для професіоналів.", "link": "#"}
    return None

# --- ЗАПУСК ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Офіційна база даних верифікації документів</p>', unsafe_allow_html=True)

params = st.query_params
url_val = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))

_, col_m, _ = st.columns([1, 2, 1])
with col_m:
    u_input = st.text_input("", value=url_val, placeholder="Введіть номер...").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

if search_btn or url_val:
    tid = re.sub(r'[^a-zA-Z0-9]', '', u_input if search_btn else url_val)
    if tid:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            res = df[df['id'] == tid]

            if not res.empty:
                row = res.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
                d_exp = pd.to_datetime(row['date'], dayfirst=True) + timedelta(days=1095)
                is_expired = (d_exp < datetime.now())

                # QR
                qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={tid}")
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                # ВИВОД КАРТКИ З ЧОРНИМ ТЕКСТОМ
                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
                        <div style="flex: 2; min-width: 260px;">
                            <div class="label-text">Власник сертифікату</div><div class="value-text">{row['name']}</div>
                            <div class="label-text">Програма навчання</div><div class="value-text">{p_name}</div>
                            <div class="label-text">Інструктор</div><div class="value-text">{row['instructor']}</div>
                            <div class="label-text">Дата видачі</div><div class="value-text">{pd.to_datetime(row['date']).strftime('%d.%m.%Y')}</div>
                            <div class="label-text">Дійсний до</div><div class="value-text">{d_exp.strftime('%d.%m.%Y')}</div>
                        </div>
                        <div style="flex: 1; text-align: center; min-width: 140px;">
                            <img src="data:image/png;base64,{qr_b64}" width="130">
                            <div style="margin-top:10px; font-weight:800; color:{'#e74c3c' if is_expired else '#2ecc71'};">
                                ● {'НЕАКТИВНИЙ' if is_expired else 'АКТИВНИЙ'}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Реклама
                promo = get_promo_data(p_id, is_expired)
                if promo:
                    st.markdown(f"""
                    <div class="promo-banner">
                        <h4 style="color:#1a1a1a; margin:0;">{promo['title']}</h4>
                        <p style="color:#444; font-size:14px; margin:10px 0;">{promo['desc']}</p>
                        <a href="{promo['link']}" style="color:#2ecc71; font-weight:700; text-decoration:none;">ПЕРЕЙТИ →</a>
                    </div>
                    """, unsafe_allow_html=True)

                # Поширення
                st.markdown(f"""
                <div style="text-align:center; margin-top:20px;">
                    <a href="https://t.me/share/url?url=https://verify.streamlit.app/?cert_id={tid}" class="share-btn tg">Telegram</a>
                    <a href="viber://forward?text=https://verify.streamlit.app/?cert_id={tid}" class="share-btn vb">Viber</a>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Сертифікат не знайдено.")
        except Exception as e:
            st.error("Помилка підключення.")
