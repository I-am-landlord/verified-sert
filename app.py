import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import re
import base64
import os
from io import BytesIO
from datetime import datetime, timedelta

# --- 1. КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Verify Center", layout="wide")

PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

def sanitize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper() if text else ""

# --- 2. ДИЗАЙН (ВАШ МАКЕТ) ---
def inject_design():
    bg_path = "background.webp"
    bg_b64 = ""
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as f:
            bg_b64 = base64.b64encode(f.read()).decode()
    
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bg_b64}");
        background-size: 100% 600px, cover; background-attachment: fixed;
    }}
    .main-title {{ font-size: 46px; font-weight: 800; text-align: center; margin-top: 40px; color: #1a1a1a; }}
    .result-card {{
        background: white; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.06);
        padding: 40px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
    .value {{ color: #1a1a1a; font-size: 18px; font-weight: 600; margin-bottom: 20px; }}
    .st-green {{ color: #2ecc71 !important; }} .st-yellow {{ color: #f1c40f !important; }} .st-red {{ color: #e74c3c !important; }}
    
    .promo-card {{
        grid-column: span 2; position: relative; height: 160px; border-radius: 20px;
        overflow: hidden; border: 1.5px solid #1a1a1a; text-decoration: none !important;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-image: url('https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=800');
        background-size: cover; filter: brightness(0.25); transition: 0.5s;
    }}
    .promo-card:hover .promo-bg {{ filter: brightness(0.6); }}
    .promo-text {{ position: relative; z-index: 2; color: white; text-align: center; padding: 40px; }}
    
    div[data-baseweb="input"] {{ border: 2.5px solid #1a1a1a !important; border-radius: 14px !important; }}
    .stButton > button {{ background: #1a1a1a !important; color: white !important; border-radius: 50px !important; padding: 10px 60px !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ГОЛОВНА ЛОГІКА ---
inject_design()
st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)

# Обробка ID
q_id = sanitize(st.query_params.get("cert_id", ""))
_, col_in, _ = st.columns([1, 2, 1])
with col_in:
    u_input = st.text_input("Пошук", value=q_id, placeholder="Номер документа", label_visibility="collapsed").strip().upper()
    clicked = st.button("ПЕРЕВІРИТИ")

final_id = sanitize(u_input if clicked else q_id)

if final_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        
        # Очищення даних таблиці
        df.columns = df.columns.str.lower().str.strip()
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().upper()
        
        match = df[df['id'] == final_id]

        if not match.empty:
            row = match.iloc[0]
            
            # Розрахунок термінів (3 роки)
            d_iss = pd.to_datetime(row['date'], dayfirst=True)
            d_exp = d_iss + timedelta(days=1095)
            days_left = (d_exp - datetime.now()).days

            # Визначення статусу
            if days_left < 0:
                cls, status = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
            elif days_left <= 30:
                cls, status = "st-yellow", "ПОТРЕБУЄ ОНОВЛЕННЯ"
            else:
                cls, status = "st-green", "АКТИВНИЙ"

            # QR
            qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={final_id}")
            buf = BytesIO()
            qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            # Вивід Картки
            st.markdown(f"""
            <div class="result-card">
                <div>
                    <div class="label">Учасник</div><div class="value">{row['name']}</div>
                    <div class="label">Курс</div><div class="value">{PROGRAMS.get(str(row['program'])[0], 'Спецкурс')}</div>
                    <div class="label">Інструктор</div><div class="value">{row['instructor']}</div>
                </div>
                <div>
                    <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                    <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                    <div class="label">Статус</div><div class="value {cls}">● {status}</div>
                </div>
                
                <a href="#" class="promo-card">
                    <div class="promo-bg"></div>
                    <div class="promo-text">
                        <div style="font-weight:800; font-size:20px;">ДОПОМОГА ТВАРИНАМ</div>
                        <div style="font-size:13px;">Знижка 15% за вашим номером сертифікату</div>
                    </div>
                </a>

                <div style="grid-column: span 2; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; padding-top: 20px;">
                    <div style="font-size: 14px; color: #aaa;">ID: {final_id}</div>
                    <img src="data:image/png;base64,{qr_b64}" width="80">
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Документ {final_id} не знайдено.")
    except Exception as e:
        st.error("Помилка бази даних. Перевірте Secrets та структуру таблиці.")
