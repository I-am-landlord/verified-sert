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

# --- СТИЛІЗАЦІЯ (ПОВНИЙ ПЕРЕНОС ВАШОГО HTML МАКЕТА) ---
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

    .main-title {{ font-size: 48px; font-weight: 800; color: #1a1a1a; text-align: center; margin-top: 50px; }}
    .sub-title {{ font-size: 18px; color: #1a1a1a; text-align: center; margin-bottom: 40px; opacity: 0.8; }}

    /* ЦЕНТРУВАННЯ ТА РОЗМІР ПОШУКУ */
    .stTextInput {{ max-width: 600px; margin: 0 auto; }}
    .stTextInput > div > div {{
        background-color: #ffffff !important;
        border: 2.5px solid #1a1a1a !important;
        border-radius: 16px !important;
        height: 70px;
    }}
    .stTextInput input {{
        font-size: 22px !important;
        text-align: center !important;
        color: #1a1a1a !important;
        padding: 20px !important;
    }}

    /* ЦЕНТРУВАННЯ КНОПКИ */
    div.stButton {{ text-align: center; }}
    div.stButton > button {{
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        padding: 15px 80px !important;
        border-radius: 50px !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        text-transform: uppercase;
        border: 2.5px solid #1a1a1a !important;
        margin-top: 20px;
    }}

    /* КАРТКА РЕЗУЛЬТАТУ */
    .result-card {{
        background: #ffffff; width: 100%; max-width: 850px; border-radius: 30px;
        border: 1px solid #e0e0e0; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        padding: 45px; margin: 30px auto; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 40px;
    }}
    .label {{ color: #888; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 1px; }}
    .value {{ color: #1a1a1a; font-size: 19px; font-weight: 600; margin-bottom: 25px; }}
    
    /* СТАТУСИ */
    .active {{ color: #2ecc71 !important; }}
    .warning {{ color: #f1c40f !important; }}
    .expired {{ color: #e74c3c !important; }}

    /* РЕКЛАМА З ЕФЕКТОМ ПРОЯВЛЕННЯ */
    .promo-card {{
        grid-column: span 2; position: relative; height: 180px; border-radius: 20px;
        overflow: hidden; border: 1.5px solid #1a1a1a; margin-top: 10px; cursor: pointer;
    }}
    .promo-bg {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.2) grayscale(1); transition: 0.5s ease;
    }}
    .promo-card:hover .promo-bg {{ filter: brightness(0.8) grayscale(0); transform: scale(1.03); }}
    .promo-text {{
        position: relative; z-index: 2; color: white; text-align: center;
        padding: 40px 20px; text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
    }}

    .alert-box {{
        grid-column: span 2; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 14px; line-height: 1.5;
        background: #fffcf0; border: 1px solid #f1c40f; color: #856404;
    }}

    .status-section {{
        grid-column: span 2; border-top: 1px solid #f0f0f0; padding-top: 25px;
        display: flex; justify-content: space-between; align-items: center;
    }}
    </style>
    """, unsafe_allow_html=True)

def get_promo_config(p_id, is_expired):
    imgs = {
        "h": "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?q=80&w=800",
        "p": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?q=80&w=800"
    }
    if is_expired or p_id == "3":
        return {"t": "ОНОВЛЕННЯ ЗНАНЬ", "d": "Перегляньте актуальний розклад тренінгів", "img": imgs['h']}
    if p_id in ["1", "2"]:
        return {"t": "ДОПОМОГА ТВАРИНАМ", "d": "Навчіться рятувати чотирилапих друзів!", "img": imgs['p']}
    return {"t": "КУРСИ ДЛЯ ЛЮДЕЙ", "d": "Опануйте домедичну допомогу Level 1-2", "img": imgs['h']}

# --- ПРОГРАМА ---
apply_style(BG_IMAGE)

st.markdown('<h1 class="main-title">Верифікація сертифікату</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Введіть номер вашого документа</p>', unsafe_allow_html=True)

params = st.query_params
url_id = re.sub(r'[^a-zA-Z0-9]', '', str(params.get("cert_id", "")))

u_input = st.text_input("", value=url_id, placeholder="Номер сертифікату", label_visibility="collapsed").strip().upper()
search_btn = st.button("ЗНАЙТИ")

if search_btn or url_id:
    tid = u_input if search_btn else url_id
    if tid:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=300)
            df.columns = df.columns.str.lower().str.strip()
            df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().str.upper()
            
            res = df[df['id'] == tid]

            if not res.empty:
                row = res.iloc[0]
                p_id = str(row['program']).split('.')[0].strip()
                p_name = PROGRAMS.get(p_id, f"Курс №{p_id}")
                
                # РОЗРАХУНОК СТАТУСУ
                d_iss = pd.to_datetime(row['date'], dayfirst=True)
                d_exp = d_iss + timedelta(days=1095)
                days_left = (d_exp - datetime.now()).days

                if days_left < 0:
                    cls, txt, alert = "expired", "ТЕРМІН ДІЇ ЗАВЕРШЕНО", True
                elif days_left <= 30:
                    cls, txt, alert = "warning", "ПІДХОДИТЬ ДО КІНЦЯ", True
                else:
                    cls, txt, alert = "active", "АКТИВНИЙ", False

                # QR
                qr = qrcode.make(f"https://verify.streamlit.app/?cert_id={tid}")
                buf = BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                # ВИВІД КАРТКИ
                st.markdown(f"""
                <div class="result-card">
                    <div class="column">
                        <div class="label">Учасник тренінгу</div><div class="value">{row['name']}</div>
                        <div class="label">Програма навчання</div><div class="value">{p_name}</div>
                        <div class="label">Інструктор(и)</div><div class="value">{row['instructor']}</div>
                    </div>
                    <div class="column">
                        <div class="label">Дата видачі</div><div class="value">{d_iss.strftime('%d.%m.%Y')}</div>
                        <div class="label">Дійсний до</div><div class="value">{d_exp.strftime('%d.%m.%Y')}</div>
                        <div class="label">Залишилось днів</div><div class="value {cls}">{max(0, days_left)} днів</div>
                    </div>
                    
                    {f'''<div class="alert-box">
                        Термін дії вашого сертифікату {'завершено' if days_left < 0 else 'підходить до кінця'}. 
                        Пропонуємо оновити знання, пройшовши новий тренінг.<br>
                        <a href="#" style="color:#26a69a; font-weight:700; text-decoration:none;">ЗАРЕЄСТРУВАТИСЬ →</a>
                    </div>''' if alert else ''}

                    <div class="promo-card">
                        <div class="promo-bg" style="background-image: url('{get_promo_config(p_id, days_left < 0)['img']}');"></div>
                        <div class="promo-text">
                            <div style="font-weight:800; font-size:20px;">{get_promo_config(p_id, days_left < 0)['t']}</div>
                            <div style="font-size:14px; opacity:0.9;">{get_promo_config(p_id, days_left < 0)['d']}</div>
                        </div>
                    </div>

                    <div class="status-section">
                        <div class="status-badge {cls}">● СТАТУС: {txt}</div>
                        <img src="data:image/png;base64,{qr_b64}" width="80">
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-box" style="background:#fff5f5; border-color:#e74c3c; color:#a94442; max-width:600px; margin:20px auto;">❌ Сертифікат не знайдено. Перевірте номер.</div>', unsafe_allow_html=True)
        except Exception:
            st.error("Помилка бази даних.")
