import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import base64
import re
import html
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import tempfile
import io

# --- КОНСТАНТИ ---
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

APP_URL = os.getenv("APP_URL", "https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/")
CERT_ID_PATTERN = re.compile(r'^[A-Z0-9]{1,20}$')

# --- ФУНКЦІЇ БЕЗПЕКИ ---
def sanitize_html(text):
    if pd.isna(text):
        return ""
    return html.escape(str(text))

def validate_cert_id(cert_id):
    if not cert_id:
        return False
    return bool(CERT_ID_PATTERN.match(cert_id))

def rate_limit_check():
    if 'last_search_time' not in st.session_state:
        st.session_state.last_search_time = datetime.now()
        st.session_state.search_count = 0
        return True
    
    time_diff = (datetime.now() - st.session_state.last_search_time).seconds
    
    if time_diff > 60:
        st.session_state.search_count = 0
        st.session_state.last_search_time = datetime.now()
    
    if st.session_state.search_count >= 10:
        return False
    
    st.session_state.search_count += 1
    return True

# --- ФУНКЦІЇ ФОНУ ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        st.warning(f"Не вдалося завантажити фоновий файл: {e}")
        return ""

def apply_custom_design(webp_file):
    bin_str = get_base64(webp_file) if os.path.exists(webp_file) else ""
    st.markdown(f'''
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 500px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 500px, cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    
    .block-container {{ 
        max-width: 900px !important; 
        padding-top: 5rem !important; 
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    
    /* ВИПРАВЛЕНО: Чорний колір заголовків */
    .main-title {{ 
        font-size: clamp(28px, 5vw, 48px); 
        font-weight: 800; 
        color: #000000 !important; 
        text-align: center; 
        margin-bottom: 0; 
    }}
    .sub-title {{ 
        font-size: clamp(14px, 3vw, 18px); 
        color: #000000 !important; 
        text-align: center; 
        margin-bottom: 3rem; 
        opacity: 0.8; 
    }}

    .stTextInput > div > div > input {{
        border: 2.5px solid #1a1a1a !important; 
        border-radius: 16px !important;
        padding: 20px !important; 
        font-size: clamp(16px, 3vw, 22px) !important; 
        text-align: center;
    }}
    
    /* ВИПРАВЛЕНО: Центрування кнопки */
    div.stButton {{
        display: flex;
        justify-content: center;
        width: 100%;
    }}
    
    div.stButton > button {{
        border-radius: 50px !important; 
        border: 2.5px solid #1a1a1a !important;
        background-color: #1a1a1a !important; 
        color: white !important;
        padding: 15px 80px !important; 
        font-weight: 800 !important; 
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    .result-card {{
        background: white; 
        border-radius: 30px; 
        border: 1px solid #e0e0e0;
        padding: clamp(20px, 5vw, 40px); 
        box-shadow: 0 20px 50px rgba(0,0,0,0.05);
    }}
    
    .result-content {{
        display: flex;
        flex-direction: row;
        gap: 20px;
    }}
    
    .label {{ 
        color: #888; 
        font-size: clamp(10px, 2vw, 11px); 
        font-weight: 700; 
        text-transform: uppercase; 
        margin-bottom: 4px; 
    }}
    .value {{ 
        color: #1a1a1a; 
        font-size: clamp(14px, 3vw, 18px); 
        font-weight: 600; 
        margin-bottom: 20px;
        word-wrap: break-word;
    }}
    
    .active {{ color: #2ecc71 !important; }}
    .warning {{ color: #f1c40f !important; }}
    .expired {{ color: #e74c3c !important; }}
    
    .hint {{
        text-align: center;
        font-size: 12px;
        color: #888;
        margin-top: 10px;
    }}
    
    @media (max-width: 768px) {{
        .result-content {{
            flex-direction: column !important;
        }}
        
        div.stButton > button {{
            padding: 12px 40px !important;
        }}
        
        .block-container {{
            padding-top: 2rem !important;
        }}
    }}
    </style>
    ''', unsafe_allow_html=True)

# --- ГЕНЕРАЦІЯ PDF (ВИПРАВЛЕНО) ---
def generate_certified_pdf(row, status, expiry_date, program_name, days_left):
    """Генерація PDF з використанням ReportLab - ВИПРАВЛЕНО повернення bytes"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Реєстрація шрифту
    font_path = "dejavu-sans.book.ttf"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            font_name = 'DejaVu'
        except Exception as e:
            st.warning(f"Шрифт не завантажено: {e}")
            font_name = 'Helvetica'
    else:
        font_name = 'Helvetica'
    
    # Заголовок
    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 60, "Підтвердження")
    
    c.setFont(font_name, 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    cert_id_safe = str(row['id'])[:50]
    c.drawCentredString(width/2, height - 80, f"Підтвердження актуальності сертифікату №{cert_id_safe}")
    
    # Таблиця
    c.setFillColorRGB(0, 0, 0)
    y_pos = height - 140
    
    try:
        date_str = pd.to_datetime(row['date']).strftime('%d.%m.%Y')
    except:
        date_str = str(row['date'])
    
    data = [
        ("№ сертифікату", str(row['id'])[:50]),
        ("Ім'я власника", str(row['name'])[:100]),
        ("Програма навчання", program_name[:100]),
        ("Інструктор(и)", str(row['instructor'])[:100]),
        ("Дата видачі", date_str),
        ("Дійсний до", expiry_date.strftime('%d.%m.%Y'))
    ]
    
    c.setFont(font_name, 11)
    for label, value in data:
        # Рамка
        c.rect(50, y_pos - 15, 150, 20)
        c.rect(200, y_pos - 15, 340, 20)
        
        # Текст
        c.drawString(55, y_pos - 10, label)
        c.drawCentredString(370, y_pos - 10, str(value))
        y_pos -= 20
    
    # QR-код
    try:
        app_url = f"{APP_URL}/?cert_id={row['id']}"
        qr = qrcode.make(app_url)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            qr_path = tmp_file.name
            qr.save(qr_path)
        
        c.setFont(font_name, 10)
        c.drawString(50, y_pos - 50, "Ви можете перевірити дані з цього документа")
        c.drawString(50, y_pos - 65, "відсканувавши QR-код")
        
        c.drawImage(qr_path, 420, y_pos - 100, width=100, height=100)
        
        if os.path.exists(qr_path):
            os.remove(qr_path)
    except Exception as e:
        st.warning(f"Не вдалося згенерувати QR-код: {e}")
    
    c.save()
    buffer.seek(0)
    
    # ВИПРАВЛЕНО: Повертаємо bytes напряму, без encode
    return buffer.read()

# --- ОСНОВНА ЛОГІКА ---
st.set_page_config(
    page_title="Verify Center", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

apply_custom_design("background.webp")

query_params = st.query_params
default_cert = query_params.get("cert_id", "").strip().upper()

if default_cert and not validate_cert_id(default_cert):
    st.warning("⚠️ Некоректний формат номера сертифіката в URL")
    default_cert = ""

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер вашого документа</p>', unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([1, 2, 1])
with col_mid:
    cert_id_input = st.text_input(
        "", 
        value=default_cert, 
        placeholder="Наприклад: A0001",
        max_chars=20,
        label_visibility="collapsed"
    ).strip().upper()
    
    search_clicked = st.button("ЗНАЙТИ")
    st.markdown('<p class="hint">*Якщо сертифікат не знайдено, спробуйте змінити мову введення</p>', unsafe_allow_html=True)

if (cert_id_input or search_clicked) and cert_id_input:
    if not validate_cert_id(cert_id_input):
        st.error("❌ Некоректний формат номера сертифіката. Використовуйте тільки латинські літери та цифри.")
    elif not rate_limit_check():
        st.error("⏳ Забагато запитів. Будь ласка, зачекайте хвилину.")
    else:
        try:
            with st.spinner('Пошук сертифіката...'):
                conn = st.connection("gsheets", type=GSheetsConnection)
                df = conn.read(ttl=300)
                
                df.columns = df.columns.str.strip().str.lower()
                
                required_cols = ['id', 'name', 'program', 'instructor', 'date']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ Помилка структури таблиці. Відсутні колонки: {', '.join(missing_cols)}")
                else:
                    df['id'] = df['id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
                    
                    match = df[df['id'] == cert_id_input]
                    
                    if not match.empty:
                        row = match.iloc[0].to_dict()
                        
                        safe_name = sanitize_html(row['name'])
                        safe_instructor = sanitize_html(row['instructor'])
                        
                        prog_name = PROGRAMS.get(str(row.get('program')), "Курс першої допомоги")
                        
                        try:
                            date_issued = pd.to_datetime(row['date'], dayfirst=True)
                            expiry_date = date_issued + timedelta(days=3*365)
                            now_utc = datetime.now()
                            days_left = (expiry_date - now_utc).days
                        except Exception as e:
                            st.error(f"❌ Помилка обробки дати: {e}")
                            days_left = 0
                            date_issued = datetime.now()
                            expiry_date = date_issued
                        
                        if days_left < 0:
                            status_class, status_text = "expired", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
                        elif days_left < 30:
                            status_class, status_text = "warning", "ПІДХОДИТЬ ДО ЗАВЕРШЕННЯ"
                        else:
                            status_class, status_text = "active", "АКТИВНИЙ"

                        st.markdown(f'''
                        <div class="result-card">
                            <div class="result-content">
                                <div style="flex: 1;">
                                    <div class="label">Учасник тренінгу</div>
                                    <div class="value">{safe_name}</div>
                                    <div class="label">Програма навчання</div>
                                    <div class="value">{prog_name}</div>
                                    <div class="label">Інструктор(и)</div>
                                    <div class="value">{safe_instructor}</div>
                                </div>
                                <div style="flex: 1;">
                                    <div class="label">Дата видачі</div>
                                    <div class="value">{date_issued.strftime('%d.%m.%Y')}</div>
                                    <div class="label">Дійсний до</div>
                                    <div class="value">{expiry_date.strftime('%d.%m.%Y')}</div>
                                    <div class="label">Залишилось днів дії</div>
                                    <div class="value {status_class}">{max(0, days_left)} днів</div>
                                </div>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)

                        if status_class in ["warning", "expired"]:
                            st.warning(f"⚠️ Термін дії вашого сертифікату {status_text.lower()}. Пропонуємо оновити знання!")
                            st.link_button("ЗАРЕЄСТРУВАТИСЬ НА ТРЕНІНГ", "https://your-site.com/courses")
                        
                        if status_class != "expired":
                            try:
                                pdf_data = generate_certified_pdf(row, status_text, expiry_date, prog_name, days_left)
                                st.download_button(
                                    "📥 ЗАВАНТАЖИТИ PDF ПІДТВЕРДЖЕННЯ", 
                                    pdf_data, 
                                    f"Confirm_{cert_id_input}.pdf", 
                                    "application/pdf",
                                    use_container_width=False
                                )
                            except Exception as e:
                                st.error(f"❌ Помилка генерації PDF: {e}")

                    else:
                        st.error("❌ Сертифікат не знайдено.")
                        st.info("💡 Сертифікати вносяться в базу даних впродовж 14 днів з дати проходження тренінгу.")
                        
        except Exception as e:
            st.error(f"❌ Помилка доступу до бази даних: {e}")
            st.info("Будь ласка, спробуйте пізніше або зв'яжіться з технічною підтримкою.")
