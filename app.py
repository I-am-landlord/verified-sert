import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import base64
from datetime import datetime, timedelta
from fpdf import FPDF

# --- КОНСТАНТИ ТА ПРОГРАМИ ---
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

# --- ФУНКЦІЯ ОБРОБКИ ФОНУ ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_bg(webp_file):
    if os.path.exists(webp_file):
        bin_str = get_base64(webp_file)
        st.markdown(f'''
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/webp;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
        </style>
        ''', unsafe_allow_html=True)
    else:
        st.warning(f"Файл фону {webp_file} не знайдено. Буде використано стандартний колір.")

# --- СТИЛІЗАЦІЯ ІНТЕРФЕЙСУ (Темний + Бірюзовий) ---
def apply_styles():
    st.markdown("""
    <style>
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 56px;
        font-weight: 800;
        color: #1a1a1a;
        line-height: 1.1;
        margin-bottom: 5px;
    }
    .highlight { color: #26a69a; } /* Бірюзовий */
    .sub-title {
        color: #1a1a1a;
        font-size: 19px;
        margin-bottom: 40px;
        font-weight: 500;
    }
    
    /* Стиль поля вводу */
    .stTextInput > div > div > input {
        border: 2px solid #1a1a1a !important;
        border-radius: 14px !important;
        padding: 12px !important;
        background-color: rgba(255, 255, 255, 0.85) !important;
        color: #1a1a1a !important;
    }

    /* Стиль кнопки - чорна овальна рамка */
    div.stButton > button {
        border-radius: 50px !important;
        border: 2px solid #1a1a1a !important;
        background-color: transparent !important;
        color: #1a1a1a !important;
        padding: 10px 45px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }

    /* Картка результату */
    .result-box {
        background: rgba(255, 255, 255, 0.98);
        padding: 35px;
        border-radius: 28px;
        border-left: 10px solid #26a69a;
        box-shadow: 0 12px 40px rgba(0,0,0,0.12);
        margin-top: 35px;
    }
    .label { color: #26a69a; font-size: 13px; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
    .value { color: #1a1a1a; font-size: 20px; font-weight: 600; margin-bottom: 22px; }
    </style>
    """, unsafe_allow_html=True)

# --- ГЕНЕРАЦІЯ PDF (Виправлено кирилицю) ---
def create_pdf(data, status, expiry_date, program_name):
    pdf = FPDF()
    pdf.add_page()
    
    font_path = "dejavu-sans.book.ttf"
    font_name = "Helvetica"
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", style="", fname=font_path)
        pdf.set_font("DejaVu", size=12)
        font_name = "DejaVu"
    else:
        pdf.set_font(font_name, size=12)

    pdf.set_draw_color(38, 166, 154) # Бірюзова рамка
    pdf.rect(10, 10, 190, 277)
    
    pdf.ln(30)
    pdf.set_font(font_name, size=22)
    pdf.set_text_color(38, 166, 154)
    title = "ПІДТВЕРДЖЕННЯ" if font_name == "DejaVu" else "VERIFICATION"
    pdf.cell(190, 10, title, ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font(font_name, size=12)
    pdf.set_text_color(26, 26, 26)
    
    # Вивід даних (тільки якщо DejaVu, інакше англійською щоб не було помилки)
    fields = [
        ("Власник", data['name']),
        ("Програма", program_name),
        ("Інструктор", data['instructor']),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y')),
        ("Статус", status)
    ] if font_name == "DejaVu" else [("Name", data['name']), ("Status", status)]

    for label, val in fields:
        pdf.set_x(35)
        pdf.cell(55, 10, f"{label}:")
        pdf.cell(100, 10, str(val), ln=True)

    # QR-код
    qr_text = f"Cert ID: {data['id']} | {data['name']}"
    qr = qrcode.make(qr_text)
    qr.save("qr_temp.png")
    pdf.image("qr_temp.png", x=155, y=245, w=30)
    if os.path.exists("qr_temp.png"): os.remove("qr_temp.png")
    
    return pdf.output()

# --- ОСНОВНИЙ ДОДАТОК ---
st.set_page_config(page_title="Verify Center", layout="wide")

# Встановлюємо фон та стилі
set_bg("background.webp") 
apply_styles()

# Текст заголовка
st.markdown('<h1 class="main-title">Знання, що <br><span class="highlight">рятують життя</span></h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Навчайся у зручному для себе форматі</p>', unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=300)
    df.columns = df.columns.str.strip().str.lower()
    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
except Exception as e:
    st.error(f"Помилка підключення до Google Sheets: {e}")
    st.stop()

# Верстка в колонку (ліва частина для контенту, права для фону)
col1, col2 = st.columns([1.3, 1])

with col1:
    cert_id = st.text_input("Введіть номер сертифікату:", placeholder="Наприклад: 2105").strip().upper()
    
    if st.button("ПЕРЕВІРИТИ →") and cert_id:
        match = df[df['id'] == cert_id]
        
        if not match.empty:
            row = match.iloc[0].to_dict()
            prog_name = PROGRAMS.get(str(row.get('program')), "Курс першої допомоги")
            
            try:
                date_val = pd.to_datetime(row['date'], dayfirst=True)
                expiry_date = date_val + timedelta(days=3*365)
                status_text = "АКТИВНИЙ" if expiry_date > datetime.now() else "ТЕРМІН ДІЇ ВИЙШОВ"
                
                # Картка результату
                st.markdown(f"""
                <div class="result-box">
                    <div class="label">Учасник</div>
                    <div class="value">{row['name']}</div>
                    <div class="label">Програма навчання</div>
                    <div class="value">{prog_name}</div>
                    <div class="label">Інструктор(и)</div>
                    <div class="value">{row['instructor']}</div>
                    <div class="label">Дійсний до</div>
                    <div class="value">{expiry_date.strftime('%d.%m.%Y')}</div>
                    <div style="color:#26a69a; font-weight:800; font-size:18px;">● СТАТУС: {status_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Генерація PDF
                pdf_bytes = create_pdf(row, status_text, expiry_date, prog_name)
                st.download_button(
                    label="📥 ЗАВАНТАЖИТИ PDF ПІДТВЕРДЖЕННЯ",
                    data=bytes(pdf_bytes),
                    file_name=f"Certificate_{cert_id}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error("Помилка обробки дати в таблиці.")
        else:
            st.error("Сертифікат не знайдено в базі даних.")
