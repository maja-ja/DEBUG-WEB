import streamlit as st
import pandas as pd
from google import genai
from streamlit_gsheets import GSheetsConnection
from io import StringIO

# ==========================================
# 1. 初始化設定
# ==========================================
st.set_page_config(page_title="Kadowsella Batch Editor", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1jTsd9IWQEMG6jfYmYnAJ9AO0NUIz8pp9iOku0Diyybo/edit#gid=618708785"

# 初始化 Gemini
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.5-flash" 
except Exception as e:
    st.error(f"AI 初始化失敗: {e}")

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 資料讀取 (使用快取避免頻繁請求)
# ==========================================
@st.cache_data(ttl=600)
def fetch_data(url):
    return conn.read(spreadsheet=url, ttl=0)

st.title("📑 1000列大數據批次修改器")

try:
    full_df = fetch_data(SHEET_URL)
    st.sidebar.success(f"成功連線！總計 {len(full_df)} 列資料")
except Exception as e:
    st.error(f"讀取失敗，請檢查權限或連結: {e}")
    st.stop()

# ==========================================
# 3. 批次選擇介面
# ==========================================
st.sidebar.header("🎯 批次範圍選擇")
batch_size = st.sidebar.number_input("每批處理數量", min_value=1, max_value=100, value=30)
total_rows = len(full_df)

# 計算總共有幾批
num_batches = (total_rows // batch_size) + (1 if total_rows % batch_size != 0 else 0)
batch_idx = st.sidebar.selectbox("選擇批次", range(num_batches), format_func=lambda x: f"第 {x+1} 批 (列 {x*batch_size} ~ {min((x+1)*batch_size, total_rows)})")

start_idx = batch_idx * batch_size
end_idx = min(start_idx + batch_size, total_rows)

# 擷取當前批次
current_batch_df = full_df.iloc[start_idx:end_idx].copy()

st.subheader(f"🔍 當前批次預覽 (第 {start_idx} 至 {end_idx} 列)")
st.dataframe(current_batch_df, use_container_width=True)

# ==========================================
# 4. AI 處理邏輯
# ==========================================
instruction = st.text_area("✍️ 輸入 AI 修改指令", "請優化這批單字的 visual_vibe 描述，使其更有畫面感，並確保 category 欄位分類正確。")

if st.button("🚀 開始 AI 批次修改"):
    with st.status("AI 正在處理中...", expanded=True) as status:
        st.write("正在轉換資料格式...")
        csv_context = current_batch_df.to_csv(index=False)
        
        prompt = f"""
        你是一個資料優化專家。以下是 CSV 格式的資料：
        {csv_context}
        
        任務指令：{instruction}
        
        要求：
        1. 嚴格保持 CSV 格式輸出。
        2. 欄位名稱與數量必須與輸入完全一致。
        3. 僅輸出 CSV 內容，不要包含任何解釋文字。
        """
        
        try:
            st.write("正在等待 Gemini 回傳...")
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            clean_csv = response.text.replace("```csv", "").replace("```", "").strip()
            
            # 轉回 DataFrame
            updated_batch_df = pd.read_csv(StringIO(clean_csv))
            
            # 檢查列數是否一致
            if len(updated_batch_df) == len(current_batch_df):
                st.session_state.processed_batch = updated_batch_df
                status.update(label="✅ AI 修改完成！", state="complete")
                st.subheader("✨ 修改結果預覽")
                st.data_editor(updated_batch_df, use_container_width=True)
            else:
                st.error(f"警告：AI 回傳的列數 ({len(updated_batch_df)}) 與原始列數 ({len(current_batch_df)}) 不符，請重試。")
        except Exception as e:
            st.error(f"AI 處理失敗: {e}")

# ==========================================
# 5. 寫回雲端 (局部縫合邏輯)
# ==========================================
if 'processed_batch' in st.session_state:
    if st.button("💾 確認並同步此批次到 Google Sheets"):
        try:
            with st.spinner("正在縫合資料並上傳雲端..."):
                # 1. 複製一份完整的資料
                new_full_df = full_df.copy()
                
                # 2. 將修改後的批次塞回對應位置
                # 注意：這裡使用 iloc 確保索引位置正確
                new_full_df.iloc[start_idx:end_idx] = st.session_state.processed_batch
                
                # 3. 執行更新
                conn.update(spreadsheet=SHEET_URL, data=new_full_df)
                
                st.success(f"✅ 成功更新第 {start_idx} 至 {end_idx} 列！")
                st.balloons()
                
                # 清除快取與暫存，強制下次讀取最新資料
                st.cache_data.clear()
                del st.session_state.processed_batch
                
        except Exception as e:
            st.error(f"同步失敗: {e}")

st.markdown("---")
st.caption("💡 提示：1000 列資料建議分 20-30 批處理，每批 30-50 列最為穩定。")