import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    # 強制清洗資料
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🎯 精準去重工具 (勾選刪除版)")
st.caption("規則：單字 + 分類 + 定義 完全一致才會判定為重複。一字多義會被安全保留。")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

# 備份原始資料進行運算
df = st.session_state.raw_df.copy()

# --- 核心邏輯：建立聯合索引來判斷重複 ---
df['check_key'] = (
    df['word'].str.lower().str.strip() + "|" + 
    df['category'].str.lower().str.strip() + "|" + 
    df['definition'].str.lower().str.strip()
)

# 找出重複項 (keep=False 代表所有重複的都列出來)
duplicate_mask = df.duplicated(subset=['check_key'], keep=False)
duplicate_df = df[duplicate_mask & (df['word'] != "")].copy()
duplicate_df = duplicate_df.sort_values(by=['word', 'category'])

if not duplicate_df.empty:
    # 1. 新增一個「刪除」欄位，預設為 False (不勾選)
    duplicate_df.insert(0, "刪除", False)
    
    st.warning(f"🔍 發現 {len(duplicate_df)} 筆完全重複的記錄：")

    # 2. 使用 data_editor 渲染，並將「刪除」欄設為 Checkbox
    edited_duplicates = st.data_editor(
        duplicate_df.drop(columns=['check_key']),
        column_config={
            "刪除": st.column_config.CheckboxColumn(
                "刪除?",
                help="勾選後點擊下方按鈕即可從資料庫移除",
                default=False,
            )
        },
        disabled=["word", "category", "definition", "roots", "breakdown"], # 防止誤改內容，只准勾選
        hide_index=True,
        use_container_width=True,
        key="duplicate_editor"
    )

    # 3. 處理刪除邏輯
    # 找出被勾選的原始索引 (Index)
    to_delete_indices = edited_duplicates[edited_duplicates["刪除"] == True].index

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"已勾選 {len(to_delete_indices)} 筆資料。")
    
    with col2:
        if st.button("🔥 確認刪除勾選項目", type="primary", use_container_width=True):
            if len(to_delete_indices) > 0:
                # 從原始 Session State 中移除這些索引
                st.session_state.raw_df = st.session_state.raw_df.drop(to_delete_indices)
                st.success("✅ 已從暫存記憶體中移除！")
                st.rerun()
            else:
                st.error("請先勾選要刪除的項目。")

    # 4. 下載最終檔案
    st.divider()
    st.subheader("💾 匯出最終資料庫")
    st.write("清理完畢後，請下載此 CSV 並上傳覆蓋回 Google Sheets。")
    
    final_csv = st.session_state.raw_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載清理後的 CSV (全表)",
        data=final_csv,
        file_name="cleaned_etymon_database.csv",
        mime="text/csv",
        use_container_width=True
    )

else:
    st.success("🎉 檢查完畢！目前資料庫非常乾淨，沒有「單字+分類+定義」完全重複的項目。")

# 顯示目前的資料庫總覽 (排除輔助列)
with st.expander("👀 查看當前資料庫總覽"):
    st.dataframe(st.session_state.raw_df, use_container_width=True)
