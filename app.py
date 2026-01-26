import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.set_page_config(layout="wide") # 強制寬螢幕，減少捲動機率
st.title("🎯 極簡勾選去重 (固定佈局版)")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df.copy()

# 重複判定邏輯
df['check_key'] = (
    df['word'].str.lower().str.strip() + "|" + 
    df['category'].str.lower().str.strip() + "|" + 
    df['definition'].str.lower().str.strip()
)

duplicate_mask = df.duplicated(subset=['check_key'], keep=False)
duplicate_df = df[duplicate_mask & (df['word'] != "")].copy()
duplicate_df = duplicate_df.sort_values(by=['word'])

if not duplicate_df.empty:
    duplicate_df.insert(0, "刪除", False)
    
    # 只顯示這四項，確保不產生橫向捲軸
    display_cols = ["刪除", "word", "example", "translation"]
    
    st.warning(f"🔍 發現 {len(duplicate_df)} 筆重複項。勾選框已固定於最左側：")

    # --- 關鍵：使用固定寬度配置 ---
    edited_df = st.data_editor(
        duplicate_df,
        column_order=display_cols,
        column_config={
            "刪除": st.column_config.CheckboxColumn(
                "❌", 
                help="勾選以刪除", 
                default=False,
                width="small" # 固定小寬度
            ),
            "word": st.column_config.TextColumn("單字", width="medium"),
            "example": st.column_config.TextColumn("例句 (比對重點)", width="large"),
            "translation": st.column_config.TextColumn("翻譯", width="medium")
        },
        disabled=["word", "example", "translation"], 
        hide_index=True,
        use_container_width=True, # 讓表格填滿畫面，避免捲動
        key="fixed_editor"
    )

    to_delete_indices = edited_df[edited_df["刪除"] == True].index

    if len(to_delete_indices) > 0:
        st.error(f"⚠️ 已選取 {len(to_delete_indices)} 筆項目")
        if st.button("🔥 確定執行刪除", use_container_width=True, type="primary"):
            st.session_state.raw_df = st.session_state.raw_df.drop(to_delete_indices)
            st.success("刪除成功！")
            st.rerun()
            
    st.divider()
    final_csv = st.session_state.raw_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載修正後的 CSV", final_csv, "cleaned.csv", use_container_width=True)

else:
    st.success("✅ 沒有重複項。")

with st.expander("查看目前完整資料庫"):
    st.dataframe(st.session_state.raw_df, use_container_width=True)
