import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import base64
import time
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

# --- Захист від перебору ---
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "blocked_until" not in st.session_state:
    st.session_state.blocked_until = 0

now = time.time()
if now < st.session_state.blocked_until:
    wait = int(st.session_state.blocked_until - now)
    st.error(f"Забагато спроб. Спробуйте через {wait} сек.")
    st.stop()

# --- СТИЛІ ---
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

    input#hp {{ display:none; }}

    .main-title {{ font-size: 42px; font-weight: 800; text-align: center; margin-top: 30px; }}
    .sub-title {{ font-size: 18px; text-align: center; margin-bottom: 30px; opacity: 0.8; }}

    div[data-baseweb="input"] {{
        background-color: white !important;
        border: 2.5px solid #1a1a1a !important;
        border-radius: 16px !important;
    }}

    input {{
        font-size: 20px !important;
        text-align: center !important;
    }}

    .stButton {{ display: flex; justify-content: center; }}

    .stButton > button {{
        background-color: #1a1a1a !important;
        color: white !important;
        padding: 14px 60px !important;
        border-radius: 50px !important;
        font-weight: 800 !important;
        border: 2.5px solid #1a1a1a !important;
    }}

    .result-card {{
        animation: fadeUp 0.5s ease-out;
        background: #fff;
        width: 100%;
        max-width: 850px;
        border-radius: 26px;
        border: 1px solid #eee;
        box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 32px;
        margin: 25px auto;
        display: grid;
        grid-template-columns: 1.2fr 0.8fr;
        gap: 25px;
    }}

    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(15px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .label {{
        color: #888;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }}

    .value {{
        font-size: 17px;
        font-weight: 600;
        margin-bottom: 18px;
        word-wrap: break-word;
    }}

    .st-green {{ color: #2ecc71; font-weight: 800; }}
    .st-yellow {{ color: #f1c40f; font-weight: 800; }}
    .st-red {{ color: #e74c3c; font-weight: 800; }}

    /* 📱 Мобільна адаптація */
    @media (max-width: 768px) {{
        .main-title {{ font-size: 30px; }}
        .sub-title {{ font-size: 15px; }}

        .result-card {{
            grid-template-columns: 1fr;
            padding: 22px;
        }}

        .stButton > button {{
            width: 100%;
            padding: 14px !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

apply_style(BG_IMAGE)

# --- UI ---
st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер документа для перевірки</p>', unsafe_allow_html=True)

# Honeypot (анти-бот)
bot_trap = st.text_input("Не заповнювати", key="hp", label_visibility="collapsed")
if bot_trap:
    st.stop()

# Отримання cert_id з URL
query_params = st.query_params
default_id = query_params.get("cert_id", "")
if isinstance(default_id, list):
    default_id = default_id[0]
default_id = re.sub(r'[^a-zA-Z0-9]', '', str(default_id)).upper()

_, col_in, _ = st.columns([1, 2, 1])
with col_in:
    cert_input = st.text_input("", value=default_id, placeholder="ВВЕДІТЬ НОМЕР...")
    st.button("ЗНАЙТИ")

final_id = cert_input.strip().upper()

# --- ЛОГІКА ---
if final_id:

    if len(final_id) > 20:
        st.error("Некоректний формат ID")
        st.stop()

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)

        df.columns = df.columns.str.lower().str.strip()
        df["id"] = df["id"].astype(str).str.split(".").str[0].str.strip().str.upper()

        match = df[df["id"] == final_id]

        if match.empty:
            st.session_state.attempts += 1

            if st.session_state.attempts >= 5:
                st.session_state.blocked_until = time.time() + 60
                st.error("Забагато спроб. Заблоковано на 60 секунд.")
                st.stop()

            st.error("Сертифікат не знайдено")
            st.stop()

        # Якщо знайдено — скидаємо лічильник
        st.session_state.attempts = 0

        row = match.iloc[0]

        p_id = str(row.get("program", "")).split(".")[0].strip()
        p_name = PROGRAMS.get(p_id, f"Спецкурс №{p_id}")

        d_iss = pd.to_datetime(str(row.get("date", "")).strip(), dayfirst=True, errors="coerce")
        if pd.isna(d_iss):
            st.error("Некоректна дата в базі")
            st.stop()

        d_exp = d_iss + timedelta(days=1095)
        days_left = (d_exp - datetime.now()).days

        if days_left < 0:
            cls, txt = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
        elif days_left <= 30:
            cls, txt = "st-yellow", "ПІДХОДИТЬ ДО КІНЦЯ"
        else:
            cls, txt = "st-green", "АКТИВНИЙ"

        share_url = f"https://your-app.streamlit.app/?cert_id={final_id}"
        qr = qrcode.make(share_url)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # --- КАРТКА ---
        st.markdown(f"""
        <div class="result-card">
            <div>
                <div class="label">Учасник тренінгу</div>
                <div class="value">{str(row.get('name','—'))}</div>

                <div class="label">Програма навчання</div>
                <div class="value">{p_name}</div>

                <div class="label">Інструктор</div>
                <div class="value">{str(row.get('instructor','—'))}</div>
            </div>

            <div>
                <div class="label">Дата видачі</div>
                <div class="value">{d_iss.strftime('%d.%m.%Y')}</div>

                <div class="label">Дійсний до</div>
                <div class="value">{d_exp.strftime('%d.%m.%Y')}</div>

                <div class="label">Залишилось днів</div>
                <div class="value"><span class="{cls}">{max(0, days_left)}</span></div>
            </div>

            <div style="grid-column: span 2; border-top: 1px solid #eee; padding-top: 20px; display: flex; justify-content: space-between; align-items: center;">
                <div class="{cls}" style="font-size: 18px; font-weight: 800;">
                    ● {txt}
                </div>
                <img src="data:image/png;base64,{qr_b64}" width="90" style="border-radius: 12px; border:1px solid #eee;">
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Помилка додатку: {e}")
