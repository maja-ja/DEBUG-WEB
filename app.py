import streamlit as st
import pandas as pd
from google import genai
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 核心配置
# ==========================================
st.set_page_config(page_title="Kadowsella AI Editor", layout="wide")

# 你的目標試算表連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/1jTsd9IWQEMG6jfYmYnAJ9AO0NUIz8pp9iOku0Diyybo/edit#gid=618708785"

# 初始化 Gemini
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.0-flash" # 或使用你偏好的模型
except Exception as e:
    st.error(f"AI 初始化失敗: {e}")

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🤖 Kadowsella 雲端自動編輯器")
st.info(f"當前目標分頁 GID: 618708785")

# ==========================================
# 2. 資料讀取
# ==========================================
try:
    # 讀取現有資料 (ttl=0 確保抓到最新)
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    st.subheader("📊 雲端現有資料")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"讀取失敗: {e}")
    st.stop()

# ==========================================
# 3. AI 自動修改邏輯
# ==========================================
st.sidebar.header("AI 修改設定")
instruction = st.sidebar.text_area("給 AI 的修改指令", 
    value="請檢查所有欄位，修正錯字，並優化 visual_vibe 的描述，使其更具畫面感。保持繁體中文。")

if st.button("🚀 啟動 AI 自動優化"):
    with st.spinner("AI 正在分析並修改資料..."):
        # 將現有資料轉為 Markdown 格式給 AI 參考
        table_context = df.to_markdown()
        
        prompt = f"""
        你現在是 Kadowsella 數據專家。
        以下是來自 Google Sheets 的資料表：
        
        {table_context}
        
        任務指令：{instruction}
        
        要求：
        1. 嚴格保持原有的欄位結構。
        2. 以 CSV 格式輸出修改後的完整表格。
        3. 不要輸出任何解釋文字，只要 CSV 內容。
        """
        
        try:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            
            # 解析 AI 回傳的 CSV (假設 AI 回傳純文字 CSV)
            from io import StringIO
            # 清理可能存在的 markdown 標籤
            csv_data = response.text.replace("```csv", "").replace("```", "").strip()
            new_df = pd.read_csv(StringIO(csv_data))
            
            st.subheader("✨ AI 修改建議預覽")
            st.data_editor(new_df, key="editor")
            st.session_state.updated_df = new_df
            
        except Exception as e:
            st.error(f"AI 處理過程中出錯: {e}")

# ==========================================
# 4. 寫回雲端
# ==========================================
if 'updated_df' in st.session_state:
    if st.button("💾 確認並同步至 Google Sheets"):
        try:
            with st.spinner("正在更新雲端資料..."):
                conn.update(
                    spreadsheet=SHEET_URL,
                    data=st.session_state.updated_df
                )
                st.success("✅ 雲端資料已成功自動修改！")
                st.balloons()
                # 清除暫存
                del st.session_state.updated_df
        except Exception as e:
            st.error(f"寫入失敗: {e}")

st.markdown("---")
st.caption("直接連線模式：讀取 -> AI 修改 -> 覆蓋更新")