import streamlit as st
import pandas as pd

# 1. 讀取並清洗資料
def load_data():
    # 使用你的試算表 ID 並強制轉 CSV 格式
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(url)
    # 強制轉字串，避免 NaN 造成 str 函數報錯
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("🧹 重複單字精確清理工具")

# 載入資料庫
if st.button("🔄 重新抓取雲端資料") or 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df.copy()

# --- 核心邏輯：過濾重複項 ---
# 統一轉小寫並去空格，確保比對精準
df['word_check'] = df['word'].str.lower().str.strip()

# keep=False 代表：只要有重複，所有重複的項目都標記為 True
duplicate_mask = df.duplicated(subset=['word_check'], keep=False)

# 排除掉空行
duplicate_df = df[duplicate_mask & (df['word_check'] != "")]

# 按單字名稱排序，讓重複的排在一起方便觀察
duplicate_df = duplicate_df.sort_values(by='word_check')

# --- 顯示介面 ---
if not duplicate_df.empty:
    st.warning(f"🚨 偵測到 {len(duplicate_df)} 筆重複記錄，共涉及 {duplicate_df['word_check'].nunique()} 個單字。")
    
    st.write("請直接在下方表格進行修改或標記，修改完成後可下載 CSV 覆蓋回雲端。")
    
    # 使用 data_editor 讓你可以直接編輯
    # 我們在這裡加入一個「刪除」勾選欄，方便你之後篩選
    duplicate_df.insert(0, "處理動作", "保留")
    
    edited_df = st.data_editor(
        duplicate_df.drop(columns=['word_check']), 
        column_config={
            "處理動作": st.column_config.SelectboxColumn(
                "處理動作",
                options=["保留", "待刪除", "需合併"],
                required=True,
            )
        },
        use_container_width=True,
        key="cleaner_editor"
    )

    # 統計目前標記
    to_delete = edited_df[edited_df["處理動作"] == "待刪除"].shape[0]
    st.info(f"📋 目前標記：{to_delete} 筆待刪除")

    # 匯出功能
    if st.button("📥 下載清理後的結果"):
        # 這裡過濾掉標記為「待刪除」的行
        final_df = edited_df[edited_df["處理動作"] != "待刪除"].drop(columns=["處理動作"])
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("確認下載修正檔案", csv, "cleaned_etymon.csv", "text/csv")
else:
    st.success("✅ 太棒了！資料庫中沒有重複的單字。")
