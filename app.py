import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

# --- 頁面設定 ---
st.set_page_config(page_title="Etymon Admin (Auto-Sync)", layout="wide")

# --- 建立連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 確保每次拿到的都是雲端最新版
    return conn.read(ttl=0).astype(str).replace('nan', '').fillna('')

def heavy_clean(text):
    return re.sub(r'\s+', '', str(text)).lower().strip()

# --- 初始化資料 ---
if 'db' not in st.session_state:
    st.session_state.db = load_data()

st.title("🛠️ Etymon 終端：自動同步版")

tab1, tab2, tab3 = st.tabs(["✨ AI 生成與篩選", "🧹 強力自動去重", "💾 雲端同步管理"])

# ==========================================
# Tab 1: AI 生成與篩選
# ==========================================
with tab1:
    if st.button("🪄 模擬 AI 生成待選單字"):
        new_items = []
        for i in range(25):
            new_items.append({
                'category': 'General', 'roots': 'temp', 'meaning': 'temp',
                'word': f'NewWord_{i}', 'breakdown': 'pre+root', 'definition': 'AI生成的定義',
                'phonetic': '/temp/', 'example': f'Example for {i}',
                'translation': '範例翻譯', 'selected': True
            })
        st.session_state.temp_batch = pd.DataFrame(new_items)
    
    if 'temp_batch' in st.session_state:
        edited_batch = st.data_editor(st.session_state.temp_batch, use_container_width=True)
        if st.button("🚀 確認加入暫存庫"):
            final_to_add = edited_batch[edited_batch['selected'] == True].drop(columns=['selected'])
            st.session_state.db = pd.concat([st.session_state.db, final_to_add], ignore_index=True)
            st.success("已加入暫存！")
            del st.session_state.temp_batch

# ==========================================
# Tab 2: 強力自動去重
# ==========================================
with tab2:
    curr_df = st.session_state.db.copy()
    curr_df['match_key'] = curr_df['word'].apply(heavy_clean) + "|" + curr_df['category'].apply(heavy_clean)
    duplicates = curr_df[curr_df.duplicated(subset=['match_key'], keep='first')]
    
    st.metric("當前重複項", len(duplicates))
    
    if not duplicates.empty:
        if st.button("🔥 執行強力去重 (記憶體)", use_container_width=True):
            st.session_state.db = curr_df.drop_duplicates(subset=['match_key'], keep='first').drop(columns=['match_key'])
            st.success("去重完成！")
            st.rerun()
    else:
        st.success("✅ 目前無重複內容。")

# ==========================================
# Tab 3: 雲端同步管理 (最重要)
# ==========================================
with tab3:
    st.write("### 檢查變更")
    st.dataframe(st.session_state.db, use_container_width=True)
    
    if st.button("☁️ 將目前所有更改「同步回雲端」", type="primary", use_container_width=True):
        with st.spinner("正在寫入 Google Sheets..."):
            try:
                # 執行自動更新
                conn.update(data=st.session_state.db)
                st.balloons()
                st.success("🎉 同步成功！雲端資料庫已是最新狀態。")
            except Exception as e:
                st.error(f"寫入失敗。請檢查 Secrets 設定是否正確。錯誤：{e}")

    if st.button("🔄 放棄本地更改，重新從雲端抓取"):
        del st.session_state.db
        st.rerun()
