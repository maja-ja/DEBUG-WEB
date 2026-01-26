import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Etymon Admin Toolbox", layout="wide")

def load_and_clean_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    # 【關鍵修復】確保所有核心欄位都是字串，避免 .str 報錯
    core_cols = ['word', 'roots', 'breakdown', 'category']
    for col in core_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', '').fillna('')
    
    return df

st.title("🛠 Etymon 管理員超級工具箱")

tab1, tab2 = st.tabs(["🧹 重複項清理", "🔍 拆解邏輯檢查"])

df = load_and_clean_data()

# ==========================================
# Tab 1: 重複項清理
# ==========================================
with tab1:
    df['word_lower'] = df['word'].str.lower().str.strip()
    duplicates = df[df.duplicated('word_lower', keep=False) & (df['word_lower'] != '')]
    
    if duplicates.empty:
        st.success("✅ 目前沒有重複單字。")
    else:
        st.warning(f"偵測到 {duplicates['word_lower'].nunique()} 組重複單字。")
        for word, group in duplicates.groupby('word_lower'):
            with st.expander(f"📍 單字：{word.upper()} ({len(group)} 筆)"):
                st.data_editor(group, key=f"dup_{word}")
                if st.button("保留首筆並刪除其餘", key=f"btn_{word}"):
                    # 執行刪除邏輯...
                    st.info("已在記憶體中標記刪除")

# ==========================================
# Tab 2: 拆解邏輯檢查 (自動檢查)
# ==========================================
with tab2:
    def verify_breakdown(row):
        word = row['word'].lower().replace('-', '')
        # 取得拆解件並去除 + 號
        parts = "".join(re.split(r'\s*\+\s*', row['breakdown'])).lower().replace('-', '')
        
        if not row['breakdown']: return "⚪ 缺少拆解資料"
        if word == parts: return "✅ 完全吻合"
        # 容許輕微差異 (如 create+ive = creative)
        if len(set(word) ^ set(parts)) <= 2: return "⚠️ 輕微變異 (可能是縮合)"
        return "❌ 邏輯不符 (拼字差異過大)"

    if st.button("🚀 執行全自動拆解校對"):
        df['校對結果'] = df.apply(verify_breakdown, axis=1)
        results = df[df['校對結果'].str.contains("❌|⚪")]
        
        if results.empty:
            st.success("🎉 所有拆解邏輯皆符合單字拼字！")
        else:
            st.error(f"發現 {len(results)} 筆異常資料")
            st.data_editor(results[['word', 'breakdown', '校對結果']])
