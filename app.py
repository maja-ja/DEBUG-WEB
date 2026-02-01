import streamlit as st
import pandas as pd
from google import genai
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 核心配置與欄位定義 (黃金 9 欄)
# ==========================================
st.set_page_config(page_title="Kadowsella Admin v1.0", layout="wide")

COL_NAMES_9 = [
    'age', 'word', 'category', 'prefix', 'root', 
    'suffix', 'phonetic', 'visual_vibe', 'field_app'
]

# --- 初始化 Gemini ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.0-flash" 
except Exception as e:
    st.error(f"AI 初始化失敗: {e}")

# --- 雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg/edit?gid=751586037#gid=751586037"

# ==========================================
# 2. 側邊欄選單 (定義 menu 變數)
# ==========================================
st.sidebar.title("🧩 Kadowsella Protocol")
menu = st.sidebar.selectbox("功能選單", ["📊 資料總覽", "🏭 9欄位量產", "☁️ 雲端同步"])

# ==========================================
# 3. 核心功能邏輯
# ==========================================

# --- 功能 A: 資料總覽 ---
if menu == "📊 資料總覽":
    st.title("📊 雲端倉庫總覽")
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        # 強制對齊前 9 欄
        df = df.iloc[:, :9]
        df.columns = COL_NAMES_9
        st.session_state.db = df
        st.dataframe(df, use_container_width=True)
        st.write(f"當前庫存：{len(df)} 筆資料")
    except Exception as e:
        st.error(f"讀取失敗: {e}")

# --- 功能 B: 9 欄位量產 ---
elif menu == "🏭 9欄位量產":
    st.title("🛠 Kadowsella 全齡量產模式")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        target_age = st.selectbox("目標年齡區間 (x歲)", [i for i in range(0, 101, 5)], index=2)
        input_words = st.text_area("輸入單字 (逗號隔開)", "Algorithm, Neural Network, API")
    
    if st.button("🚀 啟動 Agent 生產線"):
        words = [w.strip() for w in input_words.split(",") if w.strip()]
        
        with st.spinner(f"正在為 {target_age} 歲打造專屬解釋..."):
            prompt = f"""
            你現在是 Kadowsella 開源計畫的專家。請針對單字清單：{words}
            產出適合「{target_age} 歲」孩子理解的 9 欄位內容。
            
            格式要求：
            1. 純文字輸出，欄位間用「|」隔開。
            2. 順序：age|word|category|prefix|root|suffix|phonetic|visual_vibe|field_app
            3. visual_vibe 必須有強烈畫面感（適合 6-10 歲）。
            4. 語言：繁體中文。
            """
            
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
            lines = response.text.strip().split('\n')
            
            new_rows = []
            for line in lines:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 9:
                    new_rows.append(parts)
            
            if new_rows:
                new_df = pd.DataFrame(new_rows, columns=COL_NAMES_9)
                st.session_state.temp_batch = new_df
                st.success(f"✅ 已產出 {len(new_df)} 筆暫存資料！")
                st.data_editor(new_df)
            else:
                st.error("產出格式異常，請重試。")

# --- 功能 C: 雲端同步 ---
elif menu == "☁️ 雲端同步":
    st.title("💾 同步至 Google Sheets")
    
    if 'temp_batch' in st.session_state:
        st.write("待上傳的新資料：")
        st.dataframe(st.session_state.temp_batch)
        
        if st.button("確認寫回雲端倉庫"):
            try:
                # 讀取舊資料並合併
                old_df = conn.read(spreadsheet=SHEET_URL, ttl=0).iloc[:, :9]
                old_df.columns = COL_NAMES_9
                updated_df = pd.concat([old_df, st.session_state.temp_batch], ignore_index=True)
                
                # 寫回雲端
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("✅ 雲端資料庫已完成橫向擴充！")
                del st.session_state.temp_batch
            except Exception as e:
                st.error(f"同步失敗: {e}")
    else:
        st.info("緩存區空空的，先去量產單字吧！")

# ==========================================
# 4. 底部宣告
# ==========================================
st.markdown("---")
st.caption("Kadowsella v1.0 Admin | 9-Column Architecture | 1號、2號、3號 Agent 聯動中")
