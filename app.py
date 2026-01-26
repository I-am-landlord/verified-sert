import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import base64
import time
import html
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

st.set_page_config(page_title="Верифікаця сертифікату", layout="wide")

# ---------------- FORCE LIGHT THEME ----------------
st.markdown("""
<style>
html, body, [class*="css"] {
    color-scheme: light !important;
    background-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- PROTECTION ----------------
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "blocked_until" not in st.session_state:
    st.session_state.blocked_until = 0

now = time.time()
if now < st.session_state.blocked_until:
    wait = int(st.session_state.blocked_until - now)
    st.error(f"Забагато спроб. Спробуйте через {wait} сек.")
    st.stop()

# ---------------- STYLE ----------------
def apply_style(bg_base64=""):
    st.markdown(f"""
    <style>
    /* Гарантовано застосовується */
    .stApp {{
        background: #f9f9f9;
    }}

    /* Фон */
    body::before {{
        content: "";
        position: fixed;
        inset: 0;
        z-index: -3;
        background: 
            radial-gradient(circle at 30% 10%, #ffffff 0%, #f3f3f3 40%, #ededed 100%);
    }}

    /* Glow */
    body::after {{
        content: "";
        position: fixed;
        inset: 0;
        z-index: -2;
        background:
            radial-gradient(circle at 20% 20%, rgba(255,255,255,0.7), transparent 60%),
            radial-gradient(circle at 80% 40%, rgba(255,255,255,0.5), transparent 65%);
        animation: floatGlow 20s ease-in-out infinite alternate;
        pointer-events: none;
    }}

    @keyframes floatGlow {{
        from {{ background-position: 0% 0%, 100% 0%; }}
        to   {{ background-position: 15% 10%, 85% 20%; }}
    }}

    /* Grain */
    .stApp::after {{
        content: "";
        position: fixed;
        inset: 0;
        z-index: -1;
        pointer-events: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
        opacity: 0.4;
    }}

    /* Заголовки */
    .main-title {{
        font-size: 44px;
        font-weight: 800;
        text-align: center;
        margin-top: 40px;
    }}

    .sub-title {{
        text-align: center;
        font-size: 18px;
        opacity: 0.6;
        margin-bottom: 30px;
    }}

    /* Інпут */
    div[data-baseweb="input"] {{
        border-radius: 18px !important;
        border: 2px solid #111 !important;
        background: rgba(255,255,255,0.7) !important;
        backdrop-filter: blur(12px);
    }}

    input {{
        text-align: center !important;
        font-size: 18px !important;
        padding: 14px !important;
    }}

    /* Кнопка */
    .stButton > button {{
        background: linear-gradient(180deg, #111, #000);
        color: white;
        padding: 14px 50px;
        border-radius: 999px;
        font-weight: 700;
        border: none;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }}
    </style>
    """, unsafe_allow_html=True)
# ---------------- UI ----------------
st.markdown('<div class="main-title">Верифікація сертифікату</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Введіть номер сертифікату для перевірки</div>', unsafe_allow_html=True)


# URL param
query_params = st.query_params
default_id = query_params.get("cert_id", "")
if isinstance(default_id, list):
    default_id = default_id[0]

default_id = re.sub(r'[^A-Z0-9]', '', str(default_id).upper())

_, col, _ = st.columns([1, 2, 1])
with col:
    cert_input = st.text_input("", value=default_id, placeholder="Введіть номер...")
    st.button("Перевірити")

final_id = cert_input.strip().upper()

# ---------------- VALIDATION ----------------
if final_id:

    if not re.fullmatch(r"[A-Z0-9]{3,20}", final_id):
        st.error("Некоректний формат сертифіката")
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
                st.session_state.blocked_until = time.time() + 90
                st.error("Забагато спроб. Блокування 90 секунд.")
                st.stop()
            st.error("Сертифікат не знайдено")
            st.stop()

        st.session_state.attempts = 0
        row = match.iloc[0]

        # Escape everything from table
        name = html.escape(str(row.get("name", "—")))
        instructor = html.escape(str(row.get("instructor", "—")))

        p_id = html.escape(str(row.get("program", "")).split(".")[0].strip())
        p_name = html.escape(PROGRAMS.get(p_id, f"Спецкурс №{p_id}"))

        d_iss = pd.to_datetime(row.get("date"), dayfirst=True, errors="coerce")
        d_exp = d_iss + timedelta(days=1095)
        days_left = (d_exp - datetime.now()).days

        if days_left < 0:
            color, txt = "#e74c3c", "Термін дії завершено"
        elif days_left <= 30:
            color, txt = "#f1c40f", "Термін дії підходить до завершення"
        else:
            color, txt = "#2ecc71", "Активний"

        share_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={final_id}"
        qr = qrcode.make(share_url)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # ---------------- CARD ----------------
        components.html(f"""
        <div style="
            max-width:860px;
            margin:30px auto;
            background:rgba(255,255,255,0.6);
            backdrop-filter:blur(18px) saturate(180%);
            border-radius:32px;
            padding:32px;
            box-shadow:0 40px 120px rgba(0,0,0,0.08);
            animation:fadeUp .5s ease;
            font-family:system-ui;
        ">
            <div style="display:grid;grid-template-columns:1.2fr .8fr;gap:30px;">
                <div>
                    <div style="opacity:.5;font-size:12px;">Учасник</div>
                    <div style="font-size:22px;font-weight:700;">{name}</div><br>

                    <div style="opacity:.5;font-size:12px;">Програма</div>
                    <div style="font-weight:600;">{p_name}</div><br>

                    <div style="opacity:.5;font-size:12px;">Інструктори</div>
                    <div style="font-weight:600;">{instructor}</div>
                </div>

                <div>
                    <div style="opacity:.5;font-size:12px;">Дата видачі</div>
                    <div>{d_iss.strftime('%d.%m.%Y')}</div><br>

                    <div style="opacity:.5;font-size:12px;">Дійсний до</div>
                    <div>{d_exp.strftime('%d.%m.%Y')}</div><br>

                    <div style="opacity:.5;font-size:12px;">Залишилось</div>
                    <div style="font-size:22px;font-weight:800;">{max(0, days_left)}</div>
                </div>
            </div>

            <div style="margin-top:20px;border-top:1px solid #eee;padding-top:15px;display:flex;justify-content:space-between;">
                <div style="font-weight:800;color:{color};">● {txt}</div>
                <img src="data:image/png;base64,{qr_b64}" width="90" style="border-radius:14px;border:1px solid #eee;">
            </div>
        </div>

        <style>
        @keyframes fadeUp {{
            from {{ opacity:0; transform:translateY(10px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
        @media(max-width:768px){{
            div[style*="grid-template-columns"] {{
                grid-template-columns:1fr!important;
            }}
        }}
        </style>
        """, height=520)

    except Exception as e:
        st.error("Внутрішня помилка сервера")
