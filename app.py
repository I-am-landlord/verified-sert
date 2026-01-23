import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import os
import re
import base64
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

# --- СТИЛІЗАЦІЯ (МАКСИМАЛЬНА ВІДПОВІДНІСТЬ ВАШОМУ МАКЕТУ) ---
def apply_style(webp_file):
    bin_str = ""
    if os.path.exists(webp_file):
        with open(webp_file, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
            
    st.markdown(f"""
    <style>
    /* Фон */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 600px), 
                    url("data:image/webp;base64,{bin_str}");
        background-size: 100% 600px, cover;
        background-attachment: fixed;
    }}

    .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 40px; }}
    .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 20px; opacity: 0.8; }}

    /* ПОЛЕ ВВОДУ: ВЕЛИКЕ ТА БІЛЕ */
    .stTextInput > div > div {{
        background-color: #ffffff !important;
        border: 2.5px solid #1a1a1a !important;
        border-radius: 16px !important;
        min-height: 65px;
    }}
    .stTextInput input {{
        font-size: 22px !important;
        text-align: center !important;
        color: #1a1a1a !important;
    }}

    /* ЦЕНТРУВАННЯ КНОПКИ */
    div.stButton {{
        display: flex;
        justify-content: center;
    }}
    div.stButton > button {{
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        padding: 15px 80px !important;
        border-radius: 50px !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        text-transform: uppercase;
        border: 2.5px solid #1a1a1a !important;
    }}

    /* КАРТКА РЕЗУЛЬТАТУ */
    .result-card {{
        background: #ffffff; width: 100%; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 40px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}
    .value {{ color: #1a1a1a; font-size: 19px; font-weight: 600; margin-bottom: 20px; }}
    
    /* ІНДИКАЦІЯ СТАТУСІВ */
    .st-green {{ color: #2ecc71 !important; font-weight: 800; }}
    .st-yellow {{ color: #f1c40f !important; font-weight: 800; }}
    .st-red {{ color: #e74c3c !important; font-weight: 800; }}

    /* РЕКЛАМНИЙ БЛОК */
    .promo-card {{
        grid-column: span 2; position: relative; height: 160px; border-radius: 20px;
        overflow: hidden; border: 1px solid #1a1a1a; margin-top: 10px;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.25) grayscale(1); transition: 0.5s ease;
    }}
    .promo-card:hover .promo-bg {{ filter: brightness(0.7) grayscale(0); }}
    .promo-text {{
        position: relative; z-index: 2; color: white; text-align: center;
        padding: 35px 20px;
    }}

    .alert-warning-box {{
        grid-column: span 2; padding: 15px; border-radius: 15px;
        background: #fffcf0; border: 1px solid #f1c40f; color: #856404;
        text-align: center; font-size: 14px;
    }}
    </style>
    """, unsafe_allow_html=True)

def get_promo(p_id, is_expired):
    imgs = {
        "human": "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?auto=format&fit=crop&w=800",
        "pets": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=800"
    }
    if is_expired:
        return {"t": "ПОНОВІТЬ ЗНАННЯ", "d": "Ваш сертифікат прострочено. Отримайте знижку на новий курс!", "img": imgs['human']}
    if p_id in ["1", "2"]:
        return {"t": "ДОПОМОГА ТВАРИНАМ", "d": "Вмієте рятувати людей? Навчіться допомагати і тваринам!", "img": imgs['pets']}
    return {"t": "КУРСИ ПЕРШОЇ ДОПОМОГИ", "d": "Опануйте повний курс домедичної допомоги (Level 1-2)", "img": imgs['human']}

# --- ЛОГІКА ПРОГРАМИ ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер вашого документа</p>', unsafe_allow_html=True)

# Контейнер для пошуку (центрування через колонки Streamlit)
_, search_col, _ = st.columns([1, 2, 1])
with search_col:
    params = st.query_params
    url_id = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))
    u_input = st.text_input("", value=url_id, placeholder="Номер сертифікату", label_visibility="collapsed").strip().upper()
    search_clicked = st.button("ЗНАЙТИ")

if search_clicked or url_id:
    target_id = u_input if search_clicked else url_id
    if target_id:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            match = df[df['id'] == target_id]

            if not match.empty:
                row = match.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
                
                # Розрахунок термінів
                d_iss = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = d_iss + timedelta(days=1095)
                days_left = (d_exp - datetime.now()).days

                # Кольорова індикація
                if days_left < 0:
                    status_cls, status_txt, show_alert = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО", True
                elif days_left <= 30:
                    status_cls, status_txt, show_alert = "st-yellow", "ПІДХОДИТЬ ДО КІНЦЯ", True
                else:
                    status_cls, status_txt, show_alert = "st-green", "АКТИВНИЙ", False

                # QR
                qr = qrcode.make(f"https://verify.streamlit.app/?cert_id={target_id}")
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                # Картка
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <div class="label">Учасник тренінгу</div><div class="value">{row['name']}</div>
                        <div class="label">Програма навчання</div><div class="value">{p_name}</div>
                        <div class="label">Інструктор</div><div class="value">{row['instructor']}</div>
                    </div>
                    <div>
                        <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                        <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                        <div class="label">Залишилось днів</div><div class="value {status_cls}">{max(0, days_left)} днів</div>
                    </div>
                    
                    {f'''<div class="alert-warning-box">
                        Зверніть увагу! Ваш сертифікат {'вже недійсний' if days_left < 0 else 'скоро закінчиться'}. 
                        Радимо пройти оновлення знань.
                    </div>''' if show_alert else ''}

                    <div class="promo-card">
                        <div class="promo-bg" style="background-image: url('{get_promo(p_id, days_left < 0)['img']}');"></div>
                        <div class="promo-text">
                            <div style="font-weight:800; font-size:20px;">{get_promo(p_id, days_left < 0)['t']}</div>
                            <div style="font-size:14px; opacity:0.9;">{get_promo(p_id, days_left < 0)['d']}</div>
                        </div>
                    </div>

                    <div style="grid-column: span 2; border-top: 1px solid #eee; padding-top: 20px; display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-size: 18px; font-weight: 800;" class="{status_cls}">● СТАТУС: {status_txt}</div>
                        <img src="data:image/png;base64,{qr_b64}" width="80">
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="text-align:center; color:red; margin-top:20px;">❌ Сертифікат {target_id} не знайдено.</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error("Помилка з'єднання з базою даних.")
