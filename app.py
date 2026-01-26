import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 設定頁面
st.set_page_config(page_title="Etymon Cleaner (Beta)", layout="wide")

# 1. 讀取原始資料 (不分塊，直接讀取全表以利去重)
def load_raw_data():
    # 這裡建議直接讀取你 Google Sheets 的原始範圍
    # 假設你的資料在 Sheet1
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0) # 強制不使用快取
    return df

def save_to_gsheets(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(data=df)
    st.success("✅ 雲端資料庫已更新！")

st.title("🧹 單字庫去重與定位修改工具")
st.caption("本工具專門用於清理重複單字，並支援快速定位修改。")

if st.button("🔍 開始掃描重複項"):
    df = load_raw_data()
    
    # 2. 定位重複單字 (不分大小寫)
    df['word'] = df['word'].astype(str).fillna('')

# 2. 現在可以安全地進行字串操作了
    df['word_lower'] = df['word'].str.lower().str.strip()

# 3. (選用) 移除因為轉換空值而產生的無效列
    df = df[df['word_lower'] != 'nan'] 
    df = df[df['word_lower'] != '']
    duplicates = df[df.duplicated('word_lower', keep=False)]
    
    if duplicates.empty:
        st.success("🎉 太棒了！資料庫中沒有重複的單字。")
    else:
        st.warning(f"偵測到 {len(duplicates)} 筆重複記錄（涉及 {duplicates['word_lower'].nunique()} 個單字）。")
        
        # 3. 顯示重複列表並提供操作
        for word, group in duplicates.groupby('word_lower'):
            with st.expander(f"📍 重複單字：{word.upper()} (共 {len(group)} 筆)"):
                st.write("以下為資料庫中的現存記錄：")
                
                # 建立一個暫存編輯區
                edited_group = st.data_editor(
                    group.drop(columns=['word_lower']), 
                    key=f"editor_{word}",
                    num_rows="dynamic"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"🗑️ 僅保留首項並刪除其餘 - {word}", key=f"del_{word}"):
                        # 邏輯：在原 df 中刪除該字的所有索引，然後插回 edited_group 的第一筆
                        indices_to_drop = group.index
                        df = df.drop(indices_to_drop)
                        df = pd.concat([df, edited_group.head(1)], ignore_index=True)
                        st.session_state.updated_df = df
                        st.info(f"已排程刪除 {word} 的重複項，請點擊下方『同步雲端』生效。")

if "updated_df" in st.session_state:
    st.divider()
    st.subheader("💾 儲存變更")
    st.dataframe(st.session_state.updated_df)
    if st.button("🚀 確認同步至雲端 Google Sheets", type="primary"):
        save_to_gsheets(st.session_state.updated_df)
        del st.session_state.updated_df
        st.rerun()

# 4. 快速搜尋定位修改 (非重複項也能改)
st.sidebar.header("🎯 快速定位修改")
search_word = st.sidebar.text_input("輸入單字精準定位")
if search_word:
    df_all = load_raw_data()
    match = df_all[df_all['word'].str.contains(search_word, case=False, na=False)]
    if not match.empty:
        st.sidebar.write(f"找到 {len(match)} 筆結果")
        new_edit = st.data_editor(match, key="quick_edit")
        if st.sidebar.button("確認修改此筆"):
            df_all.update(new_edit)
            save_to_gsheets(df_all)
    else:
        st.sidebar.error("找不到該單字")
