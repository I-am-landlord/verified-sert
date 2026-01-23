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
import streamlit.components.v1 as components

# ---------------- CONFIG ----------------
BG_IMAGE = "background.webp"

PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# ---------------- Protection ----------------
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "blocked_until" not in st.session_state:
    st.session_state.blocked_until = 0

now = time.time()
if now < st.session_state.blocked_until:
    wait = int(st.session_state.blocked_until - now)
    st.error(f"Забагато спроб. Спробуйте через {wait} сек.")
    st.stop()

# ---------------- Style ----------------
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

    .main-title {{
        font-size: 46px;
        font-weight: 800;
        text-align: center;
        margin-top: 30px;
        letter-spacing: -1px;
    }}

    .sub-title {{
        font-size: 18px;
        text-align: center;
        opacity: 0.7;
        margin-bottom: 35px;
    }}

    div[data-baseweb="input"] {{
        border-radius: 20px !important;
        border: 2px solid #111 !important;
        background: rgba(255,255,255,0.85) !important;
        backdrop-filter: blur(6px);
    }}

    input {{
        font-size: 20px !important;
        text-align: center !important;
        padding: 12px !important;
    }}

    .stButton > button {{
        background: linear-gradient(180deg, #111, #000);
        color: white;
        border-radius: 999px;
        font-weight: 700;
        padding: 14px 60px;
        border: none;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        transition: all .2s ease;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.25);
    }}
    </style>
    """, unsafe_allow_html=True)

apply_style(BG_IMAGE)

# ---------------- UI ----------------
st.markdown('<div class="main-title">Верифікація сертифікату</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Введіть номер документа для перевірки</div>', unsafe_allow_html=True)

# Honeypot
bot_trap = st.text_input("hidden", key="hp", label_visibility="collapsed")
if bot_trap:
    st.stop()

# URL param
query_params = st.query_params
default_id = query_params.get("cert_id", "")
if isinstance(default_id, list):
    default_id = default_id[0]
default_id = re.sub(r'[^a-zA-Z0-9]', '', str(default_id)).upper()

_, col, _ = st.columns([1, 2, 1])
with col:
    cert_input = st.text_input("", value=default_id, placeholder="ВВЕДІТЬ НОМЕР...")
    st.button("ЗНАЙТИ")

final_id = cert_input.strip().upper()

# ---------------- Logic ----------------
if final_id:

    if len(final_id) > 20:
        st.error("Некоректний формат")
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
                st.error("Заблоковано на 60 секунд")
                st.stop()
            st.error("Сертифікат не знайдено")
            st.stop()

        st.session_state.attempts = 0

        row = match.iloc[0]

        p_id = str(row.get("program", "")).split(".")[0].strip()
        p_name = PROGRAMS.get(p_id, f"Спецкурс №{p_id}")

        d_iss = pd.to_datetime(row.get("date"), dayfirst=True, errors="coerce")
        d_exp = d_iss + timedelta(days=1095)
        days_left = (d_exp - datetime.now()).days

        if days_left < 0:
            cls, txt = "#e74c3c", "ТЕРМІН ЗАВЕРШЕНО"
        elif days_left <= 30:
            cls, txt = "#f1c40f", "ПІДХОДИТЬ ДО КІНЦЯ"
        else:
            cls, txt = "#2ecc71", "АКТИВНИЙ"

        share_url = f"https://your-app.streamlit.app/?cert_id={final_id}"
        qr = qrcode.make(share_url)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # ---------------- CARD ----------------
        components.html(f"""
        <div style="
            max-width: 860px;
            margin: 30px auto;
            background: rgba(255,255,255,0.75);
            backdrop-filter: blur(12px);
            border-radius: 28px;
            padding: 32px;
            box-shadow: 0 30px 80px rgba(0,0,0,0.08);
            animation: fadeUp .6s ease;
            font-family: system-ui;
        ">
            <div style="display:grid;grid-template-columns:1.2fr .8fr;gap:30px;">
                <div>
                    <div style="opacity:.5;font-size:12px;">УЧАСНИК</div>
                    <div style="font-size:22px;font-weight:700;margin-bottom:18px;">{row.get('name')}</div>

                    <div style="opacity:.5;font-size:12px;">ПРОГРАМА</div>
                    <div style="font-size:17px;font-weight:600;margin-bottom:18px;">{p_name}</div>

                    <div style="opacity:.5;font-size:12px;">ІНСТРУКТОР</div>
                    <div style="font-size:17px;font-weight:600;">{row.get('instructor')}</div>
                </div>

                <div>
                    <div style="opacity:.5;font-size:12px;">ВИДАНО</div>
                    <div style="font-weight:600;margin-bottom:16px;">{d_iss.strftime('%d.%m.%Y')}</div>

                    <div style="opacity:.5;font-size:12px;">ДІЙСНИЙ ДО</div>
                    <div style="font-weight:600;margin-bottom:16px;">{d_exp.strftime('%d.%m.%Y')}</div>

                    <div style="opacity:.5;font-size:12px;">ЗАЛИШИЛОСЬ ДНІВ</div>
                    <div style="font-size:22px;font-weight:800;">{max(0, days_left)}</div>
                </div>
            </div>

            <div style="margin-top:25px;border-top:1px solid #eee;padding-top:20px;display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:800;color:{cls};font-size:18px;">● {txt}</div>
                <img src="data:image/png;base64,{qr_b64}" width="90" style="border-radius:16px;border:1px solid #eee;">
            </div>
        </div>

        <style>
        @keyframes fadeUp {{
            from {{ opacity:0; transform:translateY(15px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
        @media(max-width:768px){{
            div[style*="grid-template-columns"] {{
                grid-template-columns:1fr !important;
            }}
        }}
        </style>
        """, height=520)

    except Exception as e:
        st.error(f"Помилка: {e}")
