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
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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

    .main-title {{ font-size: 48px; font-weight: 800; text-align: center; margin-top: 30px; }}
    .sub-title {{ font-size: 18px; text-align: center; margin-bottom: 30px; opacity: 0.8; }}

    div[data-baseweb="input"] {{ background-color: white !important; border: 2.5px solid #1a1a1a !important; border-radius: 16px !important; }}
    input {{ font-size: 20px !important; text-align: center !important; }}

    .stButton {{ display: flex; justify-content: center; }}
    .stButton > button {{
        background-color: #1a1a1a !important; color: white !important;
        padding: 15px 80px !important; border-radius: 50px !important;
        font-weight: 800 !important; border: 2.5px solid #1a1a1a !important;
    }}

    .result-card {{
        animation: fadeUp 0.6s ease-out;
        background: #fff; max-width: 850px; border-radius: 30px;
        border: 1px solid #eee; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 40px; margin: 30px auto;
        display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px;
    }}

    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    .value {{ font-size: 18px; font-weight: 600; margin-bottom: 20px; }}

    .st-green {{ color: #2ecc71; font-weight: 800; }}
    .st-yellow {{ color: #f1c40f; font-weight: 800; }}
    .st-red {{ color: #e74c3c; font-weight: 800; }}
    </style>
    """, unsafe_allow_html=True)

apply_style(BG_IMAGE)

# --- UI ---
st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер документа для перевірки</p>', unsafe_allow_html=True)

# honeypot
bot_trap = st.text_input("Не заповнювати", key="hp", label_visibility="collapsed")
if bot_trap:
    st.stop()

query_params = st.query_params
default_id = query_params.get("cert_id", "")
if isinstance(default_id, list): default_id = default_id[0]
default_id = re.sub(r'[^a-zA-Z0-9]', '', str(default_id)).upper()

_, col_in, _ = st.columns([1,2,1])
with col_in:
    cert_input = st.text_input("", value=default_id, placeholder="ВВЕДІТЬ НОМЕР...")
    search_btn = st.button("ЗНАЙТИ")

final_id = cert_input.strip().upper()

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
                st.error("Забагато спроб. Заблоковано на 60 сек.")
                st.stop()

            st.error("Сертифікат не знайдено")
            st.stop()

        st.session_state.attempts = 0
        row = match.iloc[0]

        p_id = str(row["program"]).split(".")[0].strip()
        p_name = PROGRAMS.get(p_id, f"Спецкурс №{p_id}")

        d_iss = pd.to_datetime(str(row["date"]).strip(), dayfirst=True, errors="coerce")
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

        st.markdown(f"""
        <div class="result-card">
            <div>
                <div class="label">Учасник</div>
                <div class="value">{row['name']}</div>

                <div class="label">Програма</div>
                <div class="value">{p_name}</div>

                <div class="label">Інструктор</div>
                <div class="value">{row['instructor']}</div>
            </div>

            <div>
                <div class="label">Дата видачі</div>
                <div class="value">{d_iss.strftime('%d.%m.%Y')}</div>

                <div class="label">Дійсний до</div>
                <div class="value">{d_exp.strftime('%d.%m.%Y')}</div>

                <div class="label">Залишилось днів</div>
                <div class="value"><span class="{cls}">{max(0, days_left)}</span></div>
            </div>

            <div style="grid-column: span 2; border-top:1px solid #eee; padding-top:20px; display:flex; justify-content:space-between;">
                <div class="{cls}" style="font-size:20px;">● {txt}</div>
                <img src="data:image/png;base64,{qr_b64}" width="100">
            </div>
        </div>
        """, unsafe_allow_html=True)

        # PDF
        def generate_pdf():
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            c.setFont("Helvetica", 14)

            y = 800
            for line in [
                "ПІДТВЕРДЖЕННЯ СЕРТИФІКАТУ",
                f"ID: {final_id}",
                f"Учасник: {row['name']}",
                f"Програма: {p_name}",
                f"Інструктор: {row['instructor']}",
                f"Видано: {d_iss.strftime('%d.%m.%Y')}",
                f"Дійсний до: {d_exp.strftime('%d.%m.%Y')}",
                f"Статус: {txt}"
            ]:
                c.drawString(80, y, line)
                y -= 30

            c.save()
            buffer.seek(0)
            return buffer

        st.download_button(
            "📄 Завантажити PDF підтвердження",
            data=generate_pdf(),
            file_name=f"certificate_{final_id}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Помилка: {e}")
