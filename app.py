import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# 1. 更新為新表的 ID
NEW_SHEET_URL = "https://docs.google.com/spreadsheets/d/1kOQJ2C03KHRwKROAgXQwlC_dddboMBpL-1e4jrC-mEA/edit#gid=204425767"

st.set_page_config(page_title="Etymon Admin - New DB", layout="wide")

# 初始化連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_fix_data():
    try:
        # 從新網址讀取資料 
        df = conn.read(spreadsheet=NEW_SHEET_URL, ttl=0)
        
        # 標準化欄位：去空格、轉小寫
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 移除全空行 (處理你提到的空白列問題)
        df = df.dropna(how='all')
        
        # 確保必要欄位存在
        required_cols = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        
        # 清洗字串並過濾無效列
        df = df.astype(str).replace('nan', '').fillna('')
        df = df[df['word'].str.strip() != ""]
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"讀取新表失敗，請檢查權限或網址: {e}")
        return pd.DataFrame()

# ... (其餘 heavy_clean, AI 生成與去重邏輯保持不變) ...

# --- 同步按鈕部分也要指定新網址 ---
if st.button("☁️ 同步至新雲端表", type="primary", use_container_width=True):
    try:
        # 指定寫入新表
        conn.update(spreadsheet=NEW_SHEET_URL, data=st.session_state.db)
        st.balloons()
        st.success("🎉 資料已成功寫入新表：cleaned_database_auto！")
    except Exception as e:
        st.error(f"同步失敗: {e}")
