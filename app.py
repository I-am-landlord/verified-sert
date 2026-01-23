import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import qrcode
import re
import base64
from io import BytesIO
from datetime import datetime, timedelta

# --- КОНФІГУРАЦІЯ ---
PROGRAMS = {
    "1": "6-ти годинний тренінг з першої допомоги",
    "2": "12-ти годинний тренінг з першої допомоги",
    "3": "48-ми годинний тренінг з домедичної допомоги",
    "4": "Тренінг з першої допомоги домашнім тваринам"
}

st.set_page_config(page_title="Verify Center", layout="wide")

# --- САНІТАЙЗЕР (БЕЗПЕКА) ---
def sanitize_id(input_str):
    # Видаляємо все, крім літер та цифр (Захист від XSS та ін'єкцій)
    return re.sub(r'[^a-zA-Z0-9]', '', str(input_str)).upper()

# --- CSS (БЕЗПЕЧНИЙ) ---
st.markdown("""
<style>
    .result-card {
        background: white; max-width: 800px; margin: 0 auto; padding: 30px;
        border-radius: 25px; border: 1px solid #ddd; color: black !important;
    }
    .st-green { color: #2ecc71 !important; font-weight: bold; }
    .st-yellow { color: #f1c40f !important; font-weight: bold; }
    .st-red { color: #e74c3c !important; font-weight: bold; }
    .promo-box {
        display: block; position: relative; height: 140px; border-radius: 15px;
        overflow: hidden; border: 1px solid black; margin: 15px 0;
    }
    .promo-bg {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-size: cover; background-position: center;
        filter: brightness(0.3) grayscale(1); transition: 0.5s;
    }
    .promo-box:hover .promo-bg { filter: brightness(0.7) grayscale(0); }
    .promo-text { position: relative; z-index: 2; color: white; text-align: center; padding: 35px 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Верифікація сертифікату")

# Обробка ID
raw_id = st.query_params.get("cert_id", [""])[0]
user_input = st.text_input("Введіть номер документа", value=sanitize_id(raw_id)).strip()
search_clicked = st.button("ЗНАЙТИ")

current_id = sanitize_id(user_input if search_clicked else raw_id)

if current_id:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=300)
        df.columns = df.columns.str.lower().str.strip()
        
        # Безпечний пошук у Pandas
        df['id'] = df['id'].astype(str).str.split('.').str[0].str.strip().upper()
        match = df[df['id'] == current_id]

        if not match.empty:
            row = match.iloc[0]
            
            # Логіка дат
            d_iss = pd.to_datetime(row['date'], dayfirst=True)
            d_exp = d_iss + timedelta(days=1095)
            days_left = (d_exp - datetime.now()).days

            # Вибір статусу
            if days_left < 0:
                color, status = "st-red", "ТЕРМІН ДІЇ ЗАВЕРШЕНО"
            elif days_left <= 30:
                color, status = "st-yellow", "ПІДХОДИТЬ ДО КІНЦЯ"
            else:
                color, status = "st-green", "АКТИВНИЙ"

            # Реклама (Безпечне формування)
            p_img = "https://images.unsplash.com/photo-1516589091380-5d8e87df6999?w=400"
            p_title = "ПЕРША ДОПОМОГА ТВАРИНАМ"
            
            # QR
            qr = qrcode.make(f"https://verified-sert-xyrgwme8tqwwxtpwwzmsn5.streamlit.app/?cert_id={current_id}")
            buf = BytesIO()
            qr.save(buf, format="PNG")
            qr_b64 = base64.b64encode(buf.getvalue()).decode()

            # --- ВІДОБРАЖЕННЯ (Кожен блок через окремий markdown) ---
            st.markdown(f"""
            <div class="result-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <small>УЧАСНИК</small><br><b>{row['name']}</b><br><br>
                        <small>КУРС</small><br><b>{PROGRAMS.get(str(row['program'])[0], 'Спецкурс')}</b>
                    </div>
                    <div style="text-align: right;">
                        <small>ДІЙСНИЙ ДО</small><br><b>{d_exp.strftime('%d.%m.%Y')}</b><br><br>
                        <small>ДНІВ ЗАЛИШИЛОСЬ</small><br><b class="{color}">{max(0, days_left)}</b>
                    </div>
                </div>
                
                <div class="promo-box">
                    <div class="promo-bg" style="background-image: url('{p_img}');"></div>
                    <div class="promo-text">
                        <b>{p_title}</b><br><small>Запишіться на розширений тренінг</small>
                    </div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; padding-top: 15px;">
                    <div class="{color}" style="font-size: 20px;">● {status}</div>
                    <img src="data:image/png;base64,{qr_b64}" width="80">
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.error("Документ не знайдено.")
    except Exception as e:
        st.error("Помилка доступу до даних.")
