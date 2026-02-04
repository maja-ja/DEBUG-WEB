import streamlit as st
import pandas as pd
from google import genai
from streamlit_gsheets import GSheetsConnection
from io import StringIO
import time

# ==========================================
# 1. 基礎配置
# ==========================================
st.set_page_config(page_title="Kadowsella Robot V3", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1jTsd9IWQEMG6jfYmYnAJ9AO0NUIz8pp9iOku0Diyybo/edit#gid=618708785"

# 初始化 Gemini
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.5-flash" 
except Exception as e:
    st.error(f"AI 初始化失敗: {e}")
    st.stop()

# 初始化 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🤖 Kadowsella 智能巡檢與擴張機器人 V3")
st.markdown("---")

# ==========================================
# 2. 機器人執行函式
# ==========================================

def run_robot():
    # A. 讀取資料
    with st.spinner("正在連線雲端倉庫..."):
        # 讀取時強制不使用索引，避免 MultiIndex
        df = conn.read(spreadsheet=SHEET_URL, ttl=0).reset_index(drop=True)
        
        # 確保有 21 欄 (第 21 欄索引為 20)
        while len(df.columns) < 21:
            df[f"Extra_Col_{len(df.columns)+1}"] = ""
        
        # 定義關鍵欄位位置
        WORD_COL = df.columns[1]   # 假設第 2 欄是單字
        STATUS_COL = df.columns[20] # 第 21 欄是狀態標記
        
    st.success(f"✅ 成功載入 {len(df)} 筆資料")
    
    progress_bar = st.progress(0)
    status_msg = st.empty()
    log_area = st.expander("執行日誌", expanded=True)

    # B. 第一階段：智能巡檢 (修復待辦事項)
    batch_size = 30
    total_rows = len(df)
    
    log_area.write("### 🛠 第一階段：掃描現有資料...")
    
    for i in range(0, total_rows, batch_size):
        end_idx = min(i + batch_size, total_rows)
        batch_df = df.iloc[i:end_idx].copy()
        
        # 找出需要修復的列 (第 21 欄不是 'PASS' 的)
        # 處理 NaN 的情況，確保判斷正確
        needs_repair = batch_df[batch_df[STATUS_COL].fillna("").str.upper() != "PASS"]
        
        if not needs_repair.empty:
            status_msg.text(f"正在修復第 {i} ~ {end_idx} 列...")
            
            prompt = f"""
            你是一個資料品質檢測員。以下是 CSV 資料：
            {needs_repair.to_csv(index=False)}
            
            任務：
            1. 檢查並優化內容（特別是 visual_vibe 描述）。
            2. 確保所有欄位符合 9 欄位架構。
            3. 在第 21 欄（最後一欄）填入 'PASS'。
            4. 僅回傳 CSV 內容，不要任何解釋。
            """
            
            try:
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                csv_data = response.text.replace("```csv", "").replace("```", "").strip()
                repaired_df = pd.read_csv(StringIO(csv_data)).reset_index(drop=True)
                
                if len(repaired_df) == len(needs_repair):
                    # 縫合修復後的資料
                    df.iloc[needs_repair.index] = repaired_df.values
                    log_area.write(f"✅ 已完成第 {i} ~ {end_idx} 列的優化與標記")
                    # 即時同步回雲端
                    conn.update(spreadsheet=SHEET_URL, data=df)
                else:
                    log_area.write(f"⚠️ 第 {i} 批列數不符，跳過。")
            except Exception as e:
                log_area.write(f"❌ 第 {i} 批出錯: {e}")
        else:
            log_area.write(f"⏭️ 第 {i} ~ {end_idx} 列已是 PASS，跳過。")
        
        progress_bar.progress(min((i + batch_size) / (total_rows + 100), 0.8))
        time.sleep(1) # 稍微停頓保護 API

    # C. 第二階段：自動擴張 (新增 100 筆)
    log_area.write("### 📈 第二階段：自動擴張新內容...")
    status_msg.text("正在生成 100 筆全新不重複單字...")
    
    existing_words = df[WORD_COL].dropna().unique().tolist()
    
    expansion_prompt = f"""
    參考現有風格，請再產生 100 個全新的單字與相關 9 欄位內容。
    
    已知單字清帶（請絕對不要重複）：{existing_words[:50]}... (總計 {len(existing_words)} 個)
    
    要求：
    1. 產出 100 列 CSV。
    2. 第 21 欄請直接標記為 'PASS'。
    3. 僅回傳 CSV，不要解釋。
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=expansion_prompt)
        new_csv = response.text.replace("```csv", "").replace("```", "").strip()
        new_df = pd.read_csv(StringIO(new_csv)).reset_index(drop=True)
        
        # 嚴格去重：確保新生成的單字不在舊清單中
        new_df = new_df[~new_df[WORD_COL].isin(existing_words)]
        
        # 確保欄位數量對齊
        if len(new_df.columns) < 21:
            for j in range(len(new_df.columns), 21):
                new_df[f"Col_{j+1}"] = ""
        
        # 合併並重設索引 (解決 MultiIndex 關鍵)
        final_df = pd.concat([df, new_df], ignore_index=True).reset_index(drop=True)
        
        # 最後更新
        conn.update(spreadsheet=SHEET_URL, data=final_df)
        log_area.write(f"✨ 成功擴張 {len(new_df)} 筆新單字！")
        progress_bar.progress(1.0)
        status_msg.text("🎉 機器人任務圓滿完成！")
        st.balloons()
        
    except Exception as e:
        log_area.write(f"❌ 擴張階段失敗: {e}")

# ==========================================
# 3. UI 介面
# ==========================================

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🚀 啟動智能機器人", use_container_width=True):
        run_robot()

with col_btn2:
    if st.button("🔄 重新整理預覽", use_container_width=True):
        st.cache_data.clear()

# 預覽區域
st.subheader("📊 雲端倉庫即時預覽")
try:
    # 讀取並強制重設索引，防止 MultiIndex 報錯
    preview_df = conn.read(spreadsheet=SHEET_URL, ttl=0).reset_index(drop=True)
    
    # 顯示編輯器
    st.data_editor(
        preview_df, 
        use_container_width=True, 
        height=500,
        key="main_editor"
    )
    st.caption(f"目前總行數：{len(preview_df)} | 最後一欄為品質標記位")
except Exception as e:
    st.warning(f"暫時無法顯示預覽 (可能是試算表為空或權限問題): {e}")

st.markdown("---")
st.caption("Kadowsella Robot V3 | 支援 1000+ 列自動化 | 已接入付費級 API 頻率控制")