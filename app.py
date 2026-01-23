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

# --- СТИЛІЗАЦІЯ (GLASSMORPHISM + ADAPTIVE) ---
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
    .main-title {{ font-size: clamp(32px, 7vw, 52px); font-weight: 800; color: #1a1a1a !important; text-align: center; margin-top: 50px; }}
    .sub-title {{ font-size: 18px; color: #333; text-align: center; margin-bottom: 40px; }}

    /* Біле скляне поле введення */
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 2px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 16px !important;
        color: #000 !important;
        font-size: 20px !important;
        padding: 15px !important;
        text-align: center !important;
        box-shadow: 0 8px 32px 0 rgba(255, 255, 255, 0.1) !important;
    }}

    /* Кнопки соцмереж */
    .share-btn {{ 
        display: inline-flex; align-items: center; justify-content: center; 
        padding: 12px 20px; margin: 5px; border-radius: 12px; 
        color: white !important; text-decoration: none !important; 
        font-size: 14px; font-weight: 600; transition: 0.3s; 
    }}
    .tg {{ background-color: #0088cc; }} 
    .vb {{ background-color: #7360f2; }}

    /* Рекламний блок */
    .promo-banner {{
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        border: 2px dashed #2ecc71;
        border-radius: 20px;
        padding: 25px;
        margin-top: 30px;
        text-align: center;
    }}
    .promo-btn {{ 
        background: #1a1a1a; color: white !important; 
        padding: 12px 30px; border-radius: 10px; 
        text-decoration: none; font-weight: 700; 
        display: inline-block; margin-top: 15px; 
    }}

    /* Картка результату */
    .result-card {{
        background: rgba(255, 255, 255, 0.9);
        border-radius: 30px;
        padding: clamp(20px, 5vw, 40px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 15px 35px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- ЛОГІКА РЕКЛАМИ (Cross-sell) ---
def get_promo_data(p_id, is_expired):
    if is_expired:
        return {
            "title": "🔄 Термін дії сертифікату вичерпано",
            "desc": "Ваші знання потребують актуалізації. Запишіться на повторний тренінг зі знижкою для випускників!",
            "link": "https://yoursite.com/renew"
        }
    
    # Крос-рекомендації: Тварини (4) -> Люди (1,2) і навпаки
    if p_id in ["1", "2"]:
        return {
            "title": "🐾 Турбота про чотирилапих",
            "desc": "Ви вже вмієте рятувати людей. А як щодо домашніх улюбленців? Пройдіть тренінг з допомоги тваринам!",
            "link": "https://yoursite.com/pets"
        }
    elif p_id == "4":
        return {
            "title": "👤 Допомога людям",
            "desc": "Навички допомоги тваринам у вас вже є. Опануйте домедичну допомогу для людей на наших базових курсах!",
            "link": "https://yoursite.com/human"
        }
    elif p_id == "3":
        return {
            "title": "🌟 Нові навички для профі",
            "desc": "Ви пройшли складний курс. Розширте свою експертизу іншими нашими програмами для цивільних.",
            "link": "https://yoursite.com/catalog"
        }
    return None

# --- ЗАПУСК ДОДАТКА ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Офіційна база даних верифікації документів</p>', unsafe_allow_html=True)

params = st.query_params
url_val = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))

_, col_m, _ = st.columns([1, 2, 1])
with col_m:
    u_input = st.text_input("", value=url_val, placeholder="Введіть номер документа").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

if search_btn or url_val:
    target_id = re.sub(r'[^a-zA-Z0-9]', '', u_input if search_btn else url_val)
    if target_id:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            match = df[df['id'] == target_id]

            if not match.empty:
                row = match.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
                d_iss = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = d_iss + timedelta(days=1095)
                is_expired = (d_exp < datetime.now())

                # Генерація QR-коду
                share_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={target_id}"
                qr_gen = qrcode.make(share_url)
                buf = BytesIO()
                qr_gen.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                # Вивід картки
                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center;">
                        <div style="flex: 2; min-width: 250px;">
                            <div style="color:#999; font-size:11px; font-weight:700; letter-spacing:1px;">ВЛАСНИК</div>
                            <div style="font-size:22px; font-weight:600; margin-bottom:15px;">{row['name']}</div>
                            <div style="color:#999; font-size:11px; font-weight:700; letter-spacing:1px;">КУРС</div>
                            <div style="font-size:18px; font-weight:600; margin-bottom:15px;">{p_name}</div>
                            <div style="color:#999; font-size:11px; font-weight:700; letter-spacing:1px;">СТАТУС</div>
                            <div style="font-size:18px; font-weight:800; color:{'#e74c3c' if is_expired else '#2ecc71'};">
                                ● {'ТЕРМІН ДІЇ ВИЙШОВ' if is_expired else 'ДОКУМЕНТ АКТИВНИЙ'}
                            </div>
                        </div>
                        <div style="flex: 1; text-align: center; min-width: 150px;">
                            <img src="data:image/png;base64,{qr_b64}" width="140">
                            <div style="font-size:10px; color:#bbb; margin-top:5px; font-weight:700;">QR VERIFIED</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Розумна Реклама
                promo = get_promo_data(p_id, is_expired)
                if promo:
                    st.markdown(f"""
                    <div class="promo-banner">
                        <h4 style="margin:0; color:#1a1a1a;">{promo['title']}</h4>
                        <p style="color:#444; font-size:14px; margin:10px 0;">{promo['desc']}</p>
                        <a href="{promo['link']}" class="promo-btn" target="_blank">ДІЗНАТИСЯ БІЛЬШЕ</a>
                    </div>
                    """, unsafe_allow_html=True)

                # Соцмережі
                st.markdown("<br><div style='text-align: center;'>", unsafe_allow_html=True)
                st.markdown(f"""
                    <a href="https://t.me/share/url?url={share_url}" class="share-btn tg" target="_blank">Telegram</a>
                    <a href="viber://forward?text={share_url}" class="share-btn vb" target="_blank">Viber</a>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                time.sleep(1)
                st.error("Документ не знайдено у базі даних.")
        except Exception:
            st.error("Помилка доступу до бази даних. Спробуйте пізніше.")
