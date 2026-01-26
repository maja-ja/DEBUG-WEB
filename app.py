import streamlit as st
import pandas as pd
import re

def load_data():
    sheet_id = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url)
    # 強制轉字串並處理
    df = df.astype(str).replace('nan', '').fillna('')
    return df

st.title("⚡ 強力去重模式")
st.caption("如果自動清理無效，請使用此模式。我們會強力移除所有隱藏空格與換行。")

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = load_data()

df = st.session_state.raw_df.copy()

# --- 強力清洗函數 ---
def heavy_clean(text):
    # 移除所有換行、分號、空格，並轉小寫
    text = re.sub(r'\s+', '', text) # 移除所有空白字元 (\n, \t, space)
    return text.lower().strip()

# 建立「強力比對金鑰」：只看單字和分類
df['word_clean'] = df['word'].apply(heavy_clean)
df['cat_clean'] = df['category'].apply(heavy_clean)
df['match_key'] = df['word_clean'] + "|" + df['cat_clean']

# 找出重複
duplicates = df[df.duplicated(subset=['match_key'], keep='first')]

if not duplicates.empty:
    st.warning(f"🚀 偵測到 {len(duplicates)} 筆隱藏重複項！")
    
    # 預覽被抓出來的壞傢伙
    st.dataframe(duplicates[['word', 'category', 'example']], use_container_width=True)
    
    if st.button("🔥 執行強力清理", type="primary", use_container_width=True):
        # 只保留第一筆
        df_cleaned = df.drop_duplicates(subset=['match_key'], keep='first')
        # 移除輔助欄位
        df_cleaned = df_cleaned.drop(columns=['word_clean', 'cat_clean', 'match_key'])
        
        st.session_state.raw_df = df_cleaned
        st.success(f"清理完畢！已移除 {len(duplicates)} 筆。")
        st.rerun()
else:
    st.info("💡 連強力比對都找不到重複，這代表這 1642 筆的「單字+分類」組合都是獨一無二的。")
    st.write("如果你還是覺得有重複，可能是因為同一個單字被分到了『不同的 Category』。")

# --- 檢索測試 ---
st.divider()
search = st.text_input("🔍 輸入一個你覺得重複的單字來手動檢查：")
if search:
    test = df[df['word'].str.contains(search, case=False)]
    st.write(f"搜尋結果：找到 {len(test)} 筆")
    st.table(test[['word', 'category', 'definition']])
