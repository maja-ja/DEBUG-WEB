import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    # 強制清洗資料，處理空值
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🎯 精準去重工具 (例句對照版)")
st.caption("根據 **例句與翻譯** 來判斷要保留哪一筆重複單字。")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

# 備份原始資料
df = st.session_state.raw_df.copy()

# --- 核心邏輯：判斷完全重複 (單字+分類+定義) ---
df['check_key'] = (
    df['word'].str.lower().str.strip() + "|" + 
    df['category'].str.lower().str.strip() + "|" + 
    df['definition'].str.lower().str.strip()
)

duplicate_mask = df.duplicated(subset=['check_key'], keep=False)
duplicate_df = df[duplicate_mask & (df['word'] != "")].copy()
duplicate_df = duplicate_df.sort_values(by=['word', 'category'])

if not duplicate_df.empty:
    # 1. 新增勾選欄
    duplicate_df.insert(0, "刪除", False)
    
    # 2. 定義要顯示的欄位 (隱藏後台欄位)
    display_cols = ["刪除", "word", "category", "definition", "example", "translation"]
    
    st.warning(f"🔍 發現 {len(duplicate_df)} 筆內容重複的單字，請根據例句勾選要刪除的項目：")

    # 3. 使用 data_editor 渲染
    # 我們利用 column_order 來隱藏不必要的欄位，並加寬例句欄
    edited_duplicates = st.data_editor(
        duplicate_df,
        column_order=display_cols,
        column_config={
            "刪除": st.column_config.CheckboxColumn("刪除?", default=False),
            "word": "單字",
            "category": "分類",
            "definition": "定義",
            "example": st.column_config.TextColumn("例句", width="large"),
            "translation": "翻譯"
        },
        disabled=["word", "category", "definition", "example", "translation"], 
        hide_index=True,
        use_container_width=True,
        key="duplicate_editor"
    )

    # 4. 刪除邏輯
    to_delete_indices = edited_duplicates[edited_duplicates["刪除"] == True].index

    if len(to_delete_indices) > 0:
        st.error(f"⚠️ 已選取 {len(to_delete_indices)} 筆資料準備移除")
        if st.button("🔥 執行刪除並更新清單", type="primary"):
            st.session_state.raw_df = st.session_state.raw_df.drop(to_delete_indices)
            st.success("已移除勾選項目！")
            st.rerun()
    else:
        st.info("💡 請在上方表格中勾選您不需要的重複項。")

    # 5. 下載
    st.divider()
    final_csv = st.session_state.raw_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 下載更新後的完整資料庫 (CSV)",
        final_csv,
        "updated_database.csv",
        "text/csv",
        use_container_width=True
    )
else:
    st.success("🎉 目前資料庫中沒有完全重複的項目。")

# 預覽剩餘資料
with st.expander("查看目前全表資料"):
    st.dataframe(st.session_state.raw_df, use_container_width=True)
