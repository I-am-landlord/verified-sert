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
    .main-title {{ font-size: 42px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 30px; }}
    
    /* Біле поле вводу з чорною рамкою */
    div[data-baseweb="input"] {{
        background-color: white !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
    }}
    input {{ color: #000 !important; font-size: 18px !important; text-align: center !important; }}

    /* Кнопка по центру */
    .stButton {{ display: flex; justify-content: center; }}
    .stButton > button {{
        background-color: #000 !important;
        color: #fff !important;
        padding: 10px 60px !important;
        border-radius: 50px !important;
        font-weight: 700;
        margin-top: 15px;
    }}

    /* Дизайн Картки */
    .result-card {{
        background: #ffffff;
        max-width: 800px;
        margin: 20px auto;
        padding: 35px;
        border-radius: 25px;
        border: 1px solid #ddd;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }}
    .label {{ color: #777; font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }}
    .value {{ color: #000; font-size: 18px; font-weight: 600; margin-bottom: 18px; line-height: 1.2; }}
    
    /* Статуси */
    .st-green {{ color: #2ecc71 !important; font-weight: 800; }}
    .st-yellow {{ color: #f1c40f !important; font-weight: 800; }}
    .st-red {{ color: #e74c3c !important; font-weight: 800; }}

    /* Рекламний блок */
    .promo-container {{
        position: relative;
        height: 150px;
        border-radius: 15px;
        overflow: hidden;
        margin: 20px 0;
        border: 1px solid #000;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.3) grayscale(1); transition: 0.5s;
    }}
    .promo-container:hover .promo-bg {{ filter: brightness(0.7) grayscale(0); }}
    .promo-text {{ position: relative; z-index: 2; color: #fff; text-align: center; padding: 35px 15px; }}
    
    .social-icon {{ width: 32px; margin: 0 8px; transition: 0.2s; }}
    .social-icon:hover {{ transform: scale(1.1); }}
    </style>
    """, unsafe_allow_html=True)

# --- ЛОГІКА РЕКЛАМИ ---
def get_promo_data(p_id, days_left):
    is_expired = days_left < 0
    imgs = {
        "human": "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?w=800",
        "pets": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800"
    }
    if is_expired:
        return {"t": "ПОНОВІТЬ ЗНАННЯ", "d": "Термін дії сертифіката вичерпано. Запишіться на курс зі знижкою!", "img": imgs['human'], "url": "https://yoursite.com/renew"}
    if p_id == "4":
        return {"t": "ДОПОМОГА ЛЮДЯМ", "d": "Ви вже рятуєте тварин. Час опанувати допомогу людям!", "img": imgs['human'], "url": "https://yoursite.com/human"}
    return {"t": "ДОПОМОГА ТВАРИНАМ", "d": "Станьте героєм і для чотирилапих. Наш курс допомоги тваринам!", "img": imgs['pets'], "url": "https://yoursite.com/pets"}

# --- ДОДАТОК ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)

# Обробка вводу
query_params = st.query_params
url_id = query_params.get("cert_id", "")
if isinstance(url_id, list): url_id = url_id[0]

_, col_mid, _ = st.columns([1, 1.5, 1])
with col_mid:
    user_input = st.text_input("ID", value=url_id, placeholder="Введіть номер документа", label_visibility="collapsed").strip().upper()
    search_triggered = st.button("ЗНАЙТИ")

# Кінцевий ID для пошуку
search_id = user_input if user_input else url_id
search_id = re.sub(r'[^a-zA-Z0-9]', '', str(search_id))

if search_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
        
        match = df[df['id'] == search_id]

        if not match.empty:
            row = match.iloc[0]
            p_id = str(row['program']).split('.')[0].strip()
            p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
            
            # Розрахунок статусу
            d_iss = pd.to_datetime(row['date'], dayfirst=True)
            d_exp = d_iss + timedelta(days=1095)
            days_left = (d_exp - datetime.now()).days

            if days_left < 0:
                st_cls, st_txt = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
            elif days_left <= 30:
                st_cls, st_txt = "st-yellow", "ПІДХОДИТЬ ДО КІНЦЯ"
            else:
                st_cls, st_txt = "st-green", "АКТИВНИЙ"

            # QR-код
            share_url = f"https://verify.streamlit.app/?cert_id={search_id}"
            qr_img = qrcode.make(share_url)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            # Реклама
            promo = get_promo_data(p_id, days_left)

            # --- ВИВІД КАРТКИ (ЧЕРЕЗ ОДИН HTML БЛОК ДЛЯ СТАБІЛЬНОСТІ) ---
            st.markdown(f"""
            <div class="result-card">
                <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
                    <div style="flex: 1; min-width: 250px;">
                        <div class="label">Учасник тренінгу</div><div class="value">{row['name']}</div>
                        <div class="label">Програма навчання</div><div class="value">{p_name}</div>
                        <div class="label">Інструктор</div><div class="value">{row['instructor']}</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; text-align: right;">
                        <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                        <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                        <div class="label">Залишилось днів</div><div class="value {st_cls}">{max(0, days_left)}</div>
                    </div>
                </div>

                <a href="{promo['url']}" target="_blank" style="text-decoration: none;">
                    <div class="promo-container">
                        <div class="promo-bg" style="background-image: url('{promo['img']}');"></div>
                        <div class="promo-text">
                            <div style="font-weight: 800; font-size: 18px;">{promo['t']}</div>
                            <div style="font-size: 13px; opacity: 0.9;">{promo['d']}</div>
                        </div>
                    </div>
                </a>

                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; padding-top: 20px;">
                    <div class="{st_cls}" style="font-size: 18px; font-weight: 800;">● {st_txt}</div>
                    <img src="data:image/png;base64,{qr_b64}" width="85">
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Соцмережі
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <p style="font-size: 11px; font-weight: 800; color: #555;">ПОДІЛИТИСЯ:</p>
                <a href="https://t.me/share/url?url={share_url}" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" class="social-icon"></a>
                <a href="viber://forward?text={share_url}" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/3670/3670059.png" class="social-icon"></a>
                <a href="https://api.whatsapp.com/send?text={share_url}" target="_blank"><img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" class="social-icon"></a>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.error(f"Документ №{search_id} не знайдено.")
    except Exception as e:
        st.warning("Завантаження даних... Спробуйте натиснути кнопку 'Знайти' ще раз.")
