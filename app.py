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

def apply_style():
    import streamlit as st

    st.markdown("""
    <style>
    /* ===== RESET + BASE ===== */
    html, body, [class*="st-"] {
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: linear-gradient(180deg, #f8f9fb, #eef1f5);
    }

    /* ===== CONTAINER ===== */
    section.main > div {
        max-width: 900px;
        padding-top: 2rem;
    }

    /* ===== HEADERS ===== */
    h1, h2, h3 {
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    h1 {
        text-align: center;
        font-size: 42px;
    }

    /* ===== CARDS ===== */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"]) {
        background: rgba(255,255,255,0.75);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }

    /* ===== INPUTS ===== */
    input, textarea {
        border-radius: 14px !important;
        padding: 14px !important;
        font-size: 16px !important;
        border: 1px solid #ddd !important;
        background: #fff !important;
    }

    input:focus, textarea:focus {
        border: 1px solid #000 !important;
        box-shadow: 0 0 0 2px rgba(0,0,0,0.05);
    }

    /* ===== BUTTON ===== */
    .stButton > button {
        border-radius: 999px;
        padding: 14px 36px;
        background: linear-gradient(180deg, #111, #000);
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }

    /* ===== SELECTBOX ===== */
    div[data-baseweb="select"] > div {
        border-radius: 14px;
    }

    /* ===== CHECKBOX / RADIO ===== */
    label {
        font-size: 15px;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-thumb {
        background: #ccc;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
# ---------------- FORCE LIGHT THEME ----------------


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
