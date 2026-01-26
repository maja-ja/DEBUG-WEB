import streamlit as st
import pandas as pd

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    # 強制清洗：轉字串、去空格、統一小寫處理
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🎯 精準去重工具 (一字多域保護版)")
st.caption("僅當 單字 + 分類 + 定義 完全一致時，才會判定為重複。")

if st.button("🔄 重新載入雲端數據") or 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df.copy()

# --- 核心邏輯：聯合欄位比對 ---
# 建立一個臨時的檢查列，組合三個關鍵欄位
df['check_key'] = (
    df['word'].str.lower().str.strip() + "|" + 
    df['category'].str.lower().str.strip() + "|" + 
    df['definition'].str.lower().str.strip()
)

# 執行過濾：keep=False 標記出所有完全相同的贅餘項
duplicate_mask = df.duplicated(subset=['check_key'], keep=False)
# 排除掉這三個欄位中有任何一個是空值的狀況
duplicate_df = df[duplicate_mask & (df['word'] != "") & (df['category'] != "")]

# 排序以便對比
duplicate_df = duplicate_df.sort_values(by=['word', 'category'])

if not duplicate_df.empty:
    st.warning(f"🚨 偵測到 {len(duplicate_df)} 筆完全重複的記錄。")
    
    # 加入操作欄
    duplicate_df.insert(0, "處理", "保留")
    
    # 顯示編輯器
    edited_df = st.data_editor(
        duplicate_df.drop(columns=['check_key']),
        column_config={
            "處理": st.column_config.SelectboxColumn("處理", options=["保留", "刪除"], required=True)
        },
        use_container_width=True,
        key="precision_editor"
    )

    # 匯出與下載
    if st.button("📥 生成清理後的 CSV"):
        # 邏輯：從原始 df 中移除那些在編輯器中被標記為「刪除」的資料
        # 先獲取要刪除的 index
        delete_indices = edited_df[edited_df["處理"] == "刪除"].index
        final_df = st.session_state.raw_df.drop(delete_indices)
        
        st.success(f"清理完成！原資料 {len(df)} 筆 -> 現存 {len(final_df)} 筆")
        st.download_button("確認下載 CSV", final_df.to_csv(index=False).encode('utf-8-sig'), "cleaned_etymon_v2.csv")

else:
    st.success("✅ 檢查完畢！目前資料庫中沒有完全重複的（單字+分類+定義）項目。")

# --- 側邊欄：一字多域檢查 ---
st.sidebar.header("🔍 一字多域查詢")
test_word = st.sidebar.text_input("輸入單字查看其分佈")
if test_word:
    matches = df[df['word'].str.lower().str.strip() == test_word.lower().strip()]
    if not matches.empty:
        st.sidebar.write(f"此單字在資料庫中有 {len(matches)} 個定義/分類：")
        st.sidebar.dataframe(matches[['category', 'definition']])
    else:
        st.sidebar.info("未找到相關單字。")
