import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import re
import base64
import time
import html
from io import BytesIO
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ---------------- CONFIG ----------------
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Верифікація сертифікату", layout="wide")

# ---------------- GLOBAL STYLES ----------------
st.markdown("""
<style>
/* ===== BODY & BACKGROUND ===== */
html, body, [class*="st-"] {
    margin:0; padding:0; font-family: Inter, system-ui, sans-serif;
}
.stApp {
    min-height:100vh;
    background: linear-gradient(270deg, #FBFEFE, #C1E6EF, #E7E8FA, #E7E8FA);
    background-size: 800% 800%;
    animation: gradientMove 180s ease infinite;
    display:flex;
    justify-content:center;
    align-items:center;
    padding-top:50px; 
    padding-bottom:2rem;
    flex-direction: column;
}

/* Gradient animation */
@keyframes gradientMove {
    0%{background-position:0% 50%;}
    50%{background-position:100% 50%;}
    100%{background-position:0% 50%;}
}

/* HEADERS */
.main-title {
    font-size:42px; font-weight:800; color:#222; text-align:center; margin-top:50px; margin-bottom:10px;
}
.sub-title {
    font-size:18px; font-weight:500; color:#333; text-align:center; margin-bottom:30px;
}

/* INPUT */
.stTextInput>div>div>input {
    background: rgba(255,255,255,0.6) !important;
    backdrop-filter: blur(12px) saturate(180%);
    border-radius:14px !important;
    padding:14px !important;
    font-size:16px !important;
    color:#111 !important;
}
.stTextInput>div>div>input::placeholder {color:#333 !important;}
input:focus {border:1px solid #000 !important; box-shadow:0 0 0 2px rgba(0,0,0,0.05);}

/* BUTTON */
.stButton>button {
    border-radius:999px;
    padding:14px 36px;
    background: linear-gradient(180deg, #111, #000);
    color:white;
    font-weight:600;
    border:none;
    transition: all 0.2s ease;
    display:block;
    margin:0 auto;
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}

/* ERROR MESSAGE */
.center-error {
    display: inline-block;
    background: rgba(255, 100, 100, 0.15);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 16px;
    font-weight: 600;
    color: #e74c3c;
    text-align: center;
    margin: 20px auto;
}

/* GLASS CARD ANIMATION */
@keyframes fadeUp {
    from {opacity:0; transform:translateY(10px);}
    to {opacity:1; transform:translateY(0);}
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
    st.markdown(f'<div class="center-error">Забагато спроб. Спробуйте через {wait} сек.</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- UI ----------------
st.markdown('<div class="main-title">Верифікація сертифікату</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Введіть номер сертифікату для перевірки</div>', unsafe_allow_html=True)

# ---------------- URL param ----------------
query_params = st.query_params
default_id = query_params.get("cert_id", [""])[0]
default_id = re.sub(r'[^A-Z0-9]', '', str(default_id).upper())

_, col, _ = st.columns([1,2,1])
with col:
    cert_input = st.text_input(
        "Номер сертифікату",
        value=default_id,
        placeholder="Введіть номер...",
        label_visibility="collapsed"
    )
cols = st.columns([1,2,1])
with cols[1]:
    st.button("Перевірити")

final_id = cert_input.strip().upper()

# ---------------- VALIDATION & DISPLAY ----------------
if final_id:

    if not re.fullmatch(r"[A-Z0-9]{3,20}", final_id):
        st.markdown('<div class="center-error">Некоректний формат сертифіката</div>', unsafe_allow_html=True)
        st.stop()

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        df["id"] = df["id"].astype(str).str.split(".").str[0].str.strip().str.upper()
        match = df[df["id"] == final_id]

        # ---------- SER TIFICATE NOT FOUND ----------
        if match.empty:
            st.session_state.attempts += 1
            if st.session_state.attempts >= 5:
                st.session_state.blocked_until = time.time() + 90
                st.markdown('<div class="center-error">Забагато спроб. Блокування 90 секунд.</div>', unsafe_allow_html=True)
                st.stop()
            st.markdown('<div class="center-error">Сертифікат не знайдено</div>', unsafe_allow_html=True)
            st.stop()

        # ---------- CERTIFICATE FOUND ----------
        st.session_state.attempts = 0
        row = match.iloc[0]

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

        # ---------- QR CODE ----------
        share_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={final_id}"
        qr = qrcode.make(share_url)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # ---------- GLASS CARD ----------
        components.html(f"""
        <div style="
            max-width:860px;
            margin:30px auto;
            background: rgba(255,255,255,0.4);
            backdrop-filter: blur(16px) saturate(180%);
            border-radius:32px;
            padding:32px;
            box-shadow:0 40px 120px rgba(0,0,0,0.08);
            animation:fadeUp 0.6s ease forwards;
            font-family:system-ui;
            color:#111;
        ">
            <div style="display:grid;grid-template-columns:1.2fr .8fr;gap:30px;">
                <div>
                    <div class="label">Учасник</div>
                    <div class="value">{name}</div>
                    <div class="label">Програма</div>
                    <div class="small">{p_name}</div>
                    <div class="label">Інструктори</div>
                    <div class="small">{instructor}</div>
                </div>
                <div>
                    <div class="label">Дата видачі</div>
                    <div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                    <div class="label">Дійсний до</div>
                    <div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                    <div class="label">Залишилось</div>
                    <div class="value">{max(0, days_left)} днів</div>
                </div>
            </div>
            <div style="margin-top:20px;border-top:1px solid #eee;padding-top:15px;display:flex;justify-content:space-between;">
                <div style="font-weight:800;color:{color};">● {txt}</div>
                <img src="data:image/png;base64,{qr_b64}" width="90" style="border-radius:14px;border:1px solid #eee;">
            </div>
        </div>
        """, height=520)

    except Exception as e:
        st.markdown('<div class="center-error">Внутрішня помилка сервера</div>', unsafe_allow_html=True)
