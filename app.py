import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# 頁面配置
st.set_page_config(page_title="Etymon Admin Terminal", layout="wide")

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_fix_data():
    try:
        # 強制從雲端讀取最新資料
        df = conn.read(ttl=0)
        
        # 1. 移除標題與資料中的所有隱形空白，並強制轉小寫
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 2. 移除完全空白的列 (解決截圖 2 的大量空白格問題)
        df = df.dropna(how='all')
        
        # 3. 確保必要欄位存在，防止 KeyError
        required_cols = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        
        # 4. 只保留 word 欄位有內容的有效列
        df = df[df['word'].astype(str).str.strip() != ""]
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        return pd.DataFrame(columns=['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation'])

def heavy_clean(text):
    # 用於比對的強力清洗：轉小寫、去所有空格
    return re.sub(r'\s+', '', str(text)).lower().strip()

# --- 初始化 Session State ---
if 'db' not in st.session_state:
    st.session_state.db = load_and_fix_data()

st.title("🛠️ Etymon 管理終端 (修復版)")

tab1, tab2, tab3 = st.tabs(["✨ AI 生成與篩選", "🧹 強力去重", "☁️ 同步雲端"])

# --- Tab 1: AI 生成 ---
with tab1:
    if st.button("🪄 生成 20 筆待選單字"):
        # 模擬生成，確保標題與資料庫完全一致
        mock_data = []
        for i in range(20):
            mock_data.append({
                'category': 'General', 'roots': '-', 'meaning': '-',
                'word': f'NewWord_{i}', 'breakdown': '-', 'definition': '定義',
                'phonetic': '/.../', 'example': f'Example {i}',
                'translation': '翻譯', 'keep': True
            })
        st.session_state.staging = pd.DataFrame(mock_data)

    if 'staging' in st.session_state:
        edited_staging = st.data_editor(st.session_state.staging, hide_index=True)
        if st.button("🚀 確認加入暫存庫"):
            # 僅選取打勾的列，並移除輔助欄位
            new_data = edited_staging[edited_staging['keep'] == True].drop(columns=['keep'])
            # 合併並重整索引
            st.session_state.db = pd.concat([st.session_state.db, new_data], ignore_index=True)
            st.success("已加入暫存！請切換至『強力去重』分頁處理。")
            del st.session_state.staging
            st.rerun()

# --- Tab 2: 強力去重 (解決 KeyError 之處) ---
with tab2:
    if not st.session_state.db.empty:
        df_to_clean = st.session_state.db.copy()
        
        # 建立比對金鑰 (使用緩衝檢查確保欄位存在)
        if 'word' in df_to_clean.columns and 'category' in df_to_clean.columns:
            df_to_clean['match_key'] = (
                df_to_clean['word'].apply(heavy_clean) + "|" + 
                df_to_clean['category'].apply(heavy_clean)
            )
            
            duplicates = df_to_clean[df_to_clean.duplicated(subset=['match_key'], keep='first')]
            st.metric("偵測到重複項", len(duplicates))
            
            if not duplicates.empty:
                if st.button("🔥 執行自動去重", type="primary"):
                    st.session_state.db = df_to_clean.drop_duplicates(subset=['match_key'], keep='first').drop(columns=['match_key'])
                    st.success("清理完畢！")
                    st.rerun()
        else:
            st.error("資料欄位不完整，請檢查標題列。")
    else:
        st.info("資料庫目前為空。")

# --- Tab 3: 同步雲端 ---
with tab3:
    st.dataframe(st.session_state.db, use_container_width=True)
    if st.button("☁️ 同步至 Google Sheets", type="primary", use_container_width=True):
        try:
            # 使用協作者權限直接寫回
            conn.update(data=st.session_state.db)
            st.balloons()
            st.success("🎉 雲端已同步更新！")
        except Exception as e:
            st.error(f"寫入失敗: {e}")
