import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.set_page_config(layout="wide")
st.title("⚡ 一鍵自動去重工具")
st.caption("邏輯：自動偵測「單字+分類+定義」完全重複的項目，僅保留第一筆，其餘一律刪除。")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

# --- 核心清理邏輯 ---
df_original = st.session_state.raw_df.copy()

# 建立比對特徵
df_original['check_key'] = (
    df_original['word'].str.lower().str.strip() + "|" + 
    df_original['category'].str.lower().str.strip() + "|" + 
    df_original['definition'].str.lower().str.strip()
)

# 找出重複的項目 (僅為了顯示給你看哪些被刪了)
duplicate_mask = df_original.duplicated(subset=['check_key'], keep='first')
to_delete_df = df_original[duplicate_mask]

# 執行去重 (只保留 first)
df_cleaned = df_original.drop_duplicates(subset=['check_key'], keep='first').drop(columns=['check_key'])

# --- 介面顯示 ---
col1, col2 = st.columns(2)
with col1:
    st.metric("原始總筆數", len(df_original))
with col2:
    st.metric("清理後筆數", len(df_cleaned), delta=f"-{len(to_delete_df)} 筆")

if not to_delete_df.empty:
    with st.expander("📝 查看即將被刪除的「第二筆以後」清單"):
        st.dataframe(to_delete_df[['word', 'category', 'example', 'translation']], use_container_width=True)
    
    if st.button("🔥 確認執行自動清理並下載", type="primary", use_container_width=True):
        st.session_state.raw_df = df_cleaned
        st.success("清理完成！")
        st.rerun()
else:
    st.success("✅ 檢查完畢，目前資料庫非常乾淨，沒有重複項。")

# --- 匯出功能 ---
st.divider()
final_csv = st.session_state.raw_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    "📥 下載清理後的資料庫 (CSV)",
    final_csv,
    "cleaned_database_auto.csv",
    "text/csv",
    use_container_width=True
)
