import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from streamlit_gsheets import GSheetsConnection

# 頁面配置
st.set_page_config(page_title="Etymon AI Admin Terminal", layout="wide")

# 初始化連線與 AI
conn = st.connection("gsheets", type=GSheetsConnection)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

# 定義新表 URL
NEW_DB_URL = "https://docs.google.com/spreadsheets/d/1kOQJ2C03KHRwKROAgXQwlC_dddboMBpL-1e4jrC-mEA/edit#gid=204425767"

def load_and_fix_data():
    try:
        df = conn.read(spreadsheet=NEW_DB_URL, ttl=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.dropna(how='all')
        # 確保與你提供的標題列完全一致
        required_cols = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[df['word'].astype(str).str.strip() != ""]
        return df.astype(str).replace('nan', '').fillna('').reset_index(drop=True)
    except Exception as e:
        st.error(f"資料庫載入失敗: {e}")
        return pd.DataFrame(columns=['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation'])

if 'db' not in st.session_state:
    st.session_state.db = load_and_fix_data()

st.title("🚀 Etymon AI 終端管理系統")

tab1, tab2, tab3 = st.tabs(["✨ AI 對話生成", "🧹 強力去重", "☁️ 同步雲端"])

# --- Tab 1: AI 對話生成 ---
with tab1:
    st.subheader("與 AI 對話生成單字")
    topic = st.text_input("輸入單字的主題 (例如: 希臘神話、雅思必備):")
    
    if st.button("🪄 呼叫 Gemini 生成 20 筆資料"):
        with st.spinner("AI 正在編寫單字庫..."):
            prompt = f"請生成20個關於{topic}的單字，格式為CSV(無標題)，欄位為: category, roots, meaning, word, breakdown, definition, phonetic, example, translation"
            response = model.generate_content(prompt)
            # 解析 AI 回傳文字
            raw_lines = [l.split(',') for l in response.text.strip().split('\n') if ',' in l]
            st.session_state.ai_preview = pd.DataFrame(raw_lines, columns=['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation'])

    if 'ai_preview' in st.session_state:
        st.session_state.ai_preview['selected'] = True
        edited = st.data_editor(st.session_state.ai_preview, hide_index=True)
        if st.button("🚀 確認加入暫存資料庫"):
            valid_new = edited[edited['selected'] == True].drop(columns=['selected'])
            st.session_state.db = pd.concat([st.session_state.db, valid_new], ignore_index=True)
            st.success("已成功匯入！")
            del st.session_state.ai_preview
            st.rerun()

# --- Tab 2: 強力去重 ---
with tab2:
    if not st.session_state.db.empty:
        df_clean = st.session_state.db.copy()
        def hc(x): return re.sub(r'\s+', '', str(x)).lower().strip()
        df_clean['key'] = df_clean['word'].apply(hc) + "|" + df_clean['category'].apply(hc)
        duplicates = df_clean[df_clean.duplicated(subset=['key'], keep='first')]
        
        st.metric("重複項筆數", len(duplicates))
        if st.button("🔥 一鍵強力去重"):
            st.session_state.db = df_clean.drop_duplicates(subset=['key'], keep='first').drop(columns=['key'])
            st.rerun()

# --- Tab 3: 同步雲端 ---
with tab3:
    st.dataframe(st.session_state.db, use_container_width=True)
    if st.button("☁️ 同步至 Google Sheets", type="primary", use_container_width=True):
        conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
        st.success("🎉 同步成功！")
