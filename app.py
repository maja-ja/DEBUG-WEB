import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Etymon Cleaner Beta", layout="wide")

def load_data():
    url = "https://docs.google.com/spreadsheets/d/1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg/export?format=csv"
    df = pd.read_csv(url)
    # 清洗資料防止 str 報錯
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🛠 Etymon 管理員維護工具 (Beta)")

# 載入資料
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df

tab1, tab2 = st.tabs(["🧹 重複字清理", "🔍 拆解校對"])

with tab1:
    # 建立小寫搜尋列
    df['word_clean'] = df['word'].str.lower().str.strip()
    # 找出重複 (排除空值)
    dup_mask = df.duplicated('word_clean', keep=False) & (df['word_clean'] != "")
    dups = df[dup_mask]
    
    if dups.empty:
        st.success("✅ 目前沒有發現重複單字！")
    else:
        st.warning(f"偵測到 {len(dups)} 筆重複記錄")
        # 讓使用者直接在介面改
        edited_df = st.data_editor(dups, key="dup_editor", use_container_width=True)
        
        if st.button("💾 下載修正後的 CSV"):
            # 因為我們無法自動寫回（除非你有設定 API），先提供下載備份
            st.download_button("確認下載修正檔", edited_df.to_csv(index=False).encode('utf-8-sig'), "cleaned_data.csv")

with tab2:
    if st.button("🚀 開始校對拆解邏輯"):
        def check(r):
            w = r['word'].lower().strip()
            b = "".join(re.split(r'\s*\+\s*', r['breakdown'])).lower().strip()
            if not b: return "⚪ 缺資料"
            return "✅ OK" if w == b else "❌ 不符"
        
        df['校對'] = df.apply(check, axis=1)
        errors = df[df['校對'] == "❌"]
        st.data_editor(errors[['word', 'breakdown', '校對']], use_container_width=True)

if st.sidebar.button("🔄 重新從雲端抓取"):
    st.session_state.raw_df = load_data()
    st.rerun()
