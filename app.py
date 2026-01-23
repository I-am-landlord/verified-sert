import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import time
import base64
from io import BytesIO
from datetime import datetime, timedelta
from fpdf import FPDF

# --- КОНФІГУРАЦІЯ ---
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# --- ФУНКЦІЇ БЕЗПЕКИ ТА ДИЗАЙНУ ---
def sanitize_input(user_input):
    return re.sub(r'[^a-zA-Z0-9а-яА-ЯіїєІЇЄ]', '', user_input)

def check_rate_limit():
    if "request_count" not in st.session_state:
        st.session_state.request_count = []
    curr = time.time()
    st.session_state.request_count = [t for t in st.session_state.request_count if curr - t < 60]
    if len(st.session_state.request_count) >= 10: # Збільшено до 10 для зручності
        return False
    st.session_state.request_count.append(curr)
    return True

def get_qr_base64(url):
    """Генерує QR-код у форматі base64 для відображення в HTML"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def apply_custom_design(webp_file):
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 500px), 
                        url("data:image/webp;base64,{encoded_string}");
            background-size: 100% 500px, cover;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; }}
        .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 30px; opacity: 0.8; }}
        .result-card {{ background: white; border-radius: 30px; border: 1px solid #e0e0e0; padding: 35px; box-shadow: 0 15px 40px rgba(0,0,0,0.08); }}
        .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }}
        .value {{ color: #1a1a1a; font-size: 18px; font-weight: 600; margin-bottom: 15px; }}
        .qr-container {{ text-align: center; border: 1px solid #eee; padding: 10px; border-radius: 15px; background: #fafafa; }}
        .qr-hint {{ font-size: 10px; color: #888; margin-top: 5px; font-weight: 700; }}
        .active-color {{ color: #2ecc71; font-weight: 800; }}
        .warning-color {{ color: #f1c40f; font-weight: 800; }}
        .expired-color {{ color: #e74c3c; font-weight: 800; }}
        </style>
        """, unsafe_allow_html=True)

# --- ГЕНЕРАЦІЯ PDF ---
def generate_pdf(row, expiry_date, program_name, verify_url):
    pdf = FPDF()
    pdf.add_page()
    font_file = "dejavu-sans.book.ttf"
    if os.path.exists(font_file):
        pdf.add_font("DejaVu", "", font_file, uni=True)
        pdf.set_font("DejaVu", size=12)
        f_n = "DejaVu"
    else:
        pdf.set_font("Arial", size=12)
        f_n = "Arial"

    pdf.set_font(f_n, size=22)
    pdf.cell(190, 20, "Підтвердження", ln=True, align='C')
    pdf.set_font(f_n, size=11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(190, 10, f"Верифікація сертифікату №{row['id']}", ln=True, align='C')
    pdf.ln(10)

    # Таблиця за макетом
    pdf.set_text_color(0, 0, 0)
    data = [
        ("№ сертифікату", row['id']), ("Ім'я власника", row['name']),
        ("Програма навчання", program_name), ("Інструктор(и)", row['instructor']),
        ("Дата видачі", pd.to_datetime(row['date']).strftime('%d.%m.%Y')),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y'))
    ]
    for l, v in data:
        pdf.cell(65, 12, l, border=1)
        pdf.cell(125, 12, str(v), border=1, ln=True, align='C')

    # QR на PDF
    qr_img = qrcode.make(verify_url)
    qr_img.save("pdf_qr.png")
    pdf.ln(15)
    pdf.image("pdf_qr.png", x=145, y=pdf.get_y(), w=35)
    pdf.set_font(f_n, size=9)
    pdf.text(20, pdf.get_y() + 10, "Відскануйте QR-код для миттєвої")
    pdf.text(20, pdf.get_y() + 15, "перевірки в базі даних.")
    if os.path.exists("pdf_qr.png"): os.remove("pdf_qr.png")
    return pdf.output(dest='S').encode('latin-1')

# --- ЛОГІКА ДОДАТКА ---
apply_custom_design("background.webp")

# Обробка URL параметрів (Автоматична перевірка)
params = st.query_params
url_cert_id = sanitize_input(params.get("cert_id", ""))

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Результат перевірки в офіційній базі даних</p>', unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    cert_input = st.text_input("", value=url_cert_id, placeholder="Номер документа").strip().upper()
    search_btn = st.button("ЗНАЙТИ")

# Виконуємо пошук якщо натиснута кнопка АБО якщо є ID в URL
if search_btn or url_cert_id:
    if not check_rate_limit():
        st.error("Забагато запитів! Спробуйте пізніше.")
    else:
        target_id = sanitize_input(cert_input if search_btn else url_cert_id)
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            match = df[df['id'] == target_id]
            if not match.empty:
                row = match.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Курс (ID: {p_id})")
                d_iss = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = d_iss + timedelta(days=1095)
                days = (d_exp - datetime.now()).days
                
                # Посилання для QR
                base_url = "https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/" # ЗАМІНИТИ ПІСЛЯ ДЕПЛОЮ
                verify_url = f"{base_url}/?cert_id={target_id}"
                qr_base64 = get_qr_base64(verify_url)

                status_c = "active-color" if days > 30 else "warning-color" if days >= 0 else "expired-color"
                status_t = "АКТИВНИЙ" if days > 30 else "ЗАКІНЧУЄТЬСЯ" if days >= 0 else "ТЕРМІН ЗАВЕРШЕНО"

                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="width: 50%;">
                            <div class="label">Учасник</div><div class="value">{row['name']}</div>
                            <div class="label">Програма</div><div class="value">{p_name}</div>
                            <div class="label">Інструктор</div><div class="value">{row['instructor']}</div>
                            <div class="label">Статус</div><div class="value {status_c}">● {status_t}</div>
                        </div>
                        <div style="width: 25%;">
                            <div class="label">Видано</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                            <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                            <div class="label">Днів залишилось</div><div class="value {status_c}">{max(0, days)}</div>
                        </div>
                        <div style="width: 20%;" class="qr-container">
                            <img src="data:image/png;base64,{qr_base64}" width="100%">
                            <div class="qr-hint">VERIFY QR</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                pdf_bytes = generate_pdf(row, d_exp, p_name, verify_url)
                st.download_button("📥 ЗАВАНТАЖИТИ PDF ПІДТВЕРДЖЕННЯ", pdf_bytes, f"Verify_{target_id}.pdf")
            else:
                st.error("Сертифікат не знайдено.")
        except Exception as e:
            st.error(f"Помилка підключення: {e}")
