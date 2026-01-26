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
    margin:0; padding:0; font-family: 'DejaVu', Arial, sans-serif;
}
.stApp {
    min-height:100vh;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    background: linear-gradient(270deg, #FBFEFE, #C1E6EF, #E7E8FA, #E7E8FA);
    background-size: 800% 800%;
    animation: gradientMove 180s ease infinite;
    padding: 50px 20px;
}
/* Gradient animation */
@keyframes gradientMove {
    0%{background-position:0% 50%;}
    50%{background-position:100% 50%;}
    100%{background-position:0% 50%;}
}

/* ===== MAIN CONTAINER CENTERING ===== */
.main .block-container {
    max-width: 1000px;
    margin: 0 auto;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 50vh;
}

/* ===== HEADERS ===== */
.main-title {font-size:42px; font-weight:800; color:#222; text-align:center; margin-bottom:10px; margin-top:15%}
.sub-title {font-size:18px; font-weight:500; color:#333; text-align:center; margin-bottom:30px;}

/* ===== INPUT ===== */
.stTextInput>div>div>input {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px) saturate(180%);
    border-radius:14px !important;
    padding:14px !important;
    font-size:16px !important;
    color:#111 !important;
}
.stTextInput>div>div>input::placeholder {color:#333 !important;}
input:focus {border:1px solid #000 !important; box-shadow:0 0 0 2px rgba(0,0,0,0.05);}

/* ===== BUTTON ===== */
.stButton>button {
    border-radius:999px;
    padding:14px 36px;
    background: linear-gradient(180deg, #111, #000);
    color:white;
    font-weight:600;
    border:none;
    transition: all 0.3s ease;
    display:block;
    margin:10px auto;
}
.stButton>button:hover {transform: translateY(-1px); box-shadow:0 10px 25px rgba(0,0,0,0.2);}

/* ===== ERROR CENTERED ===== */
.center-error {
    display:inline-block;
    background: rgba(255,100,100,0.15);
    backdrop-filter: blur(8px);
    border-radius:12px;
    padding:10px 20px;
    font-size:16px;
    font-weight:600;
    color:#e74c3c;
    text-align:center;
    margin:20px auto;
}
/* ===== MAIN CONTAINER CENTERING ===== */
.main .block-container {
    max-width: 1000px;
    margin: 0 auto;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 30vh;
}

/* ===== MOBILE RESPONSIVE ===== */
@media(max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 10vh;
    }
    
    .main-title {
        font-size: 32px !important;
    }
    
    .sub-title {
        font-size: 16px !important;
        margin-bottom: 20px !important;
    }
    
    .stApp {
        padding: 20px 10px !important;
    }
}

@media(max-width: 480px) {
    .main .block-container {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        padding-top: 5vh;
    }
    
    .main-title {
        font-size: 28px !important;
    }
    
    .sub-title {
        font-size: 14px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------------- PROTECTION ----------------
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "blocked_until" not in st.session_state: st.session_state.blocked_until = 0
now = time.time()
if now < st.session_state.blocked_until:
    wait = int(st.session_state.blocked_until - now)
    st.markdown(f'<div class="center-error">Забагато спроб. Спробуйте через {wait} сек.</div>', unsafe_allow_html=True)
    st.stop()

# ---------------- HEADER ----------------
st.markdown('<div class="main-title">Верифікація сертифікату</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Введіть номер сертифікату для перевірки</div>', unsafe_allow_html=True)

# ---------------- INPUT ----------------
query_params = st.query_params
default_id = query_params.get("cert_id", [""])[0]
default_id = re.sub(r'[^A-Z0-9]', '', str(default_id).upper())

_, col, _ = st.columns([1,2,1])
with col:
    cert_input = st.text_input("Номер сертифікату", value=default_id, placeholder="Введіть номер...", label_visibility="collapsed")
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
        if match.empty:
            st.session_state.attempts +=1
            if st.session_state.attempts >=5:
                st.session_state.blocked_until = time.time() + 90
                st.markdown('<div class="center-error">Забагато спроб. Блокування 90 секунд.</div>', unsafe_allow_html=True)
                st.stop()
            st.markdown('<div class="center-error">Сертифікат не знайдено</div>', unsafe_allow_html=True)
            st.stop()
        st.session_state.attempts = 0
        row = match.iloc[0]

        name = html.escape(str(row.get("name","—")))
        instructor = html.escape(str(row.get("instructor","—")))
        p_id = html.escape(str(row.get("program","")).split(".")[0].strip())
        p_name = html.escape(PROGRAMS.get(p_id,f"Спецкурс №{p_id}"))

        d_iss = pd.to_datetime(row.get("date"), dayfirst=True, errors="coerce")
        d_exp = d_iss + timedelta(days=1095)
        days_left = (d_exp - datetime.now()).days

        if days_left < 0:
            color, txt = "#e74c3c", "Термін дії завершено"
        elif days_left <=30:
            color, txt = "#f1c40f", "Термін дії підходить до завершення"
        else:
            color, txt = "#2ecc71", "Активний"

        share_url = f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={final_id}"
        qr = qrcode.make(share_url)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        # ----------- GLASS CARD -----------
        components.html(f"""
        <style>
        /* ===== GLASS CARD ===== */
        .glass-card {{
            max-width:900px;
            width:100%;
            margin:40px auto;
            background: rgba(255,255,255,0.35);
            backdrop-filter: blur(20px) saturate(180%);
            border-radius:32px;
            padding:40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            color:#111;
            font-family: 'DejaVu', Arial, sans-serif;
            animation: fadeUp 0.8s ease forwards;
        }}
        @keyframes fadeUp {{from {{opacity:0; transform:translateY(20px);}} to {{opacity:1; transform:translateY(0);}}}}
        .glass-grid {{display:grid; grid-template-columns:1.2fr .8fr; gap:30px;}}
        @media(max-width:768px){{.glass-grid {{grid-template-columns:1fr !important;}}}}
        .label {{opacity:0.6; font-size:13px; font-weight:500; margin-bottom:4px;}}
        .value {{font-size:22px; font-weight:700; margin-bottom:15px; color:#111;}}
        .small {{font-size:18px; font-weight:600; color:#111; margin-bottom:12px;}}
        .status {{font-weight:800; font-size:16px;}}
        @media(max-width:768px){
            .glass-grid {grid-template-columns:1fr !important;}
            .glass-card {
                    padding: 25px !important;
                    margin: 20px auto !important;
                    }
            .value {font-size: 20px !important;}
            .small {font-size: 16px !important;}
                    }

        @media(max-width:480px){
            .glass-card {
                padding: 20px !important;
                margin: 10px auto !important;
            }
            .value {font-size: 18px !important;}
            .small {font-size: 15px !important;}
            }
        </style>
        <div class="glass-card">
            <div class="glass-grid">
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
                    <div class="value">{max(0,days_left)} днів</div>
                </div>
            </div>
            <div style="margin-top:20px; border-top:1px solid #eee; padding-top:15px; display:flex; justify-content:space-between; align-items:center;">
                <div class="status" style="color:{color};">● {txt}</div>
                <img src="data:image/png;base64,{qr_b64}" width="90" style="border-radius:14px; border:1px solid #eee;">
            </div>
        </div>
        """, height=560)

    except Exception as e:
        st.markdown('<div class="center-error">Внутрішня помилка сервера</div>', unsafe_allow_html=True)
