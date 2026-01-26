import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# 頁面配置
st.set_page_config(page_title="Etymon Terminal", layout="wide")

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義新表 URL
NEW_DB_URL = "https://docs.google.com/spreadsheets/d/1kOQJ2C03KHRwKROAgXQwlC_dddboMBpL-1e4jrC-mEA/edit#gid=204425767"

def load_and_fix_data():
    try:
        # 強制讀取新表內容
        df = conn.read(spreadsheet=NEW_DB_URL, ttl=0)
        
        # 1. 欄位標題標準化 (移除前後空格並轉小寫)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 2. 徹底移除完全空白的列 (解決截圖中 1000 多列空白的問題)
        df = df.dropna(how='all')
        
        # 3. 檢查並補齊必要欄位，防止 KeyError
        required_cols = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        
        # 4. 只保留 'word' 欄位有文字的列，並清洗字串
        df = df[df['word'].astype(str).str.strip() != ""]
        df = df.astype(str).replace('nan', '').fillna('')
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"讀取資料庫失敗，請確認標題列是否包含 'word' 與 'category': {e}")
        return pd.DataFrame(columns=['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation'])

def heavy_clean(text):
    return re.sub(r'\s+', '', str(text)).lower().strip()

# 初始化資料庫
if 'db' not in st.session_state:
    st.session_state.db = load_and_fix_data()

st.title("🛠️ Etymon 終端：強力同步版")

tab1, tab2, tab3 = st.tabs(["✨ AI 生成篩選", "🧹 強力去重", "☁️ 同步新雲端"])

# --- Tab 1: AI 生成篩選 ---
with tab1:
    if st.button("🪄 生成 20 筆待選單字"):
        mock_data = []
        for i in range(20):
            mock_data.append({
                'category': 'General', 'roots': '-', 'meaning': '-',
                'word': f'Word_{i}', 'breakdown': '-', 'definition': '定義',
                'phonetic': '/.../', 'example': f'Example {i}',
                'translation': '翻譯', 'keep': True
            })
        st.session_state.staging = pd.DataFrame(mock_data)

    if 'staging' in st.session_state:
        edited_staging = st.data_editor(st.session_state.staging, hide_index=True)
        if st.button("🚀 確認加入暫存"):
            to_add = edited_staging[edited_staging['keep'] == True].drop(columns=['keep'])
            st.session_state.db = pd.concat([st.session_state.db, to_add], ignore_index=True)
            st.success("已加入！")
            del st.session_state.staging
            st.rerun()

# --- Tab 2: 強力去重 ---
with tab2:
    if not st.session_state.db.empty:
        df_clean = st.session_state.db.copy()
        # 建立比對金鑰
        df_clean['match_key'] = df_clean['word'].apply(heavy_clean) + "|" + df_clean['category'].apply(heavy_clean)
        duplicates = df_clean[df_clean.duplicated(subset=['match_key'], keep='first')]
        
        st.metric("偵測到重複", len(duplicates))
        if not duplicates.empty:
            if st.button("🔥 執行強力清理", use_container_width=True):
                st.session_state.db = df_clean.drop_duplicates(subset=['match_key'], keep='first').drop(columns=['match_key'])
                st.success("清理完成！")
                st.rerun()
    else:
        st.info("資料庫目前為空。")

# --- Tab 3: 同步新雲端 ---
with tab3:
    st.write(f"當前資料筆數: {len(st.session_state.db)}")
    st.dataframe(st.session_state.db, use_container_width=True)
    
    # 確保按鈕在畫面中
    if st.button("☁️ 同步至新雲端表", type="primary", use_container_width=True):
        with st.spinner("正在寫入雲端..."):
            try:
                # 自動同步回新表
                conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
                st.balloons()
                st.success("🎉 雲端已更新！重複與空白已清除。")
            except Exception as e:
                st.error(f"寫入失敗，請確認 Secrets 是否正確: {e}")
