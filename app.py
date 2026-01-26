import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    # 強制清洗資料
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🎯 精簡對照去重")
st.caption("僅顯示單字、例句與翻譯，方便快速勾選重複項。")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df.copy()

# 核心重複判斷邏輯 (維持單字+分類+定義的三重判定，確保安全)
df['check_key'] = (
    df['word'].str.lower().str.strip() + "|" + 
    df['category'].str.lower().str.strip() + "|" + 
    df['definition'].str.lower().str.strip()
)

duplicate_mask = df.duplicated(subset=['check_key'], keep=False)
duplicate_df = df[duplicate_mask & (df['word'] != "")].copy()
duplicate_df = duplicate_df.sort_values(by=['word', 'category'])

if not duplicate_df.empty:
    duplicate_df.insert(0, "刪除", False)
    
    # --- 關鍵修改：排除 definition，只留你需要的 ---
    display_cols = ["刪除", "word", "category", "example", "translation"]
    
    st.warning(f"🔍 發現 {len(duplicate_df)} 筆重複，請根據例句決定：")

    edited_duplicates = st.data_editor(
        duplicate_df,
        column_order=display_cols,
        column_config={
            "刪除": st.column_config.CheckboxColumn("刪除", default=False),
            "word": "單字",
            "category": "分類",
            "example": st.column_config.TextColumn("例句內容", width="large"),
            "translation": "中文翻譯"
        },
        disabled=["word", "category", "example", "translation"], 
        hide_index=True,
        use_container_width=True,
        key="duplicate_editor_v3"
    )

    to_delete_indices = edited_duplicates[edited_duplicates["刪除"] == True].index

    if len(to_delete_indices) > 0:
        if st.button(f"🔥 確認刪除這 {len(to_delete_indices)} 筆項目", type="primary", use_container_width=True):
            st.session_state.raw_df = st.session_state.raw_df.drop(to_delete_indices)
            st.success("刪除成功！")
            st.rerun()
    
    st.divider()
    # 提供下載按鈕以便更新雲端
    final_csv = st.session_state.raw_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載修正後的 CSV 檔", final_csv, "cleaned_data.csv", "text/csv")

else:
    st.success("✅ 資料庫目前沒有完全重複的內容。")

with st.expander("查看目前全表"):
    st.dataframe(st.session_state.raw_df, use_container_width=True)
