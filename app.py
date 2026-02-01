import streamlit as st
import pandas as pd
from google import genai

# --- 1. 核心欄位配置 (完全對接前台) ---
COL_NAMES_9 = [
    'age', 'word', 'category', 'prefix', 'root', 
    'suffix', 'phonetic', 'visual_vibe', 'field_app'
]

# --- 2. 核心量產指令 (1號生產者 + 2號校對者邏輯) ---
def generate_kadowsella_data(words_list, target_age):
    mass_prompt = f"""
    你現在是 Kadowsella 開源計畫的 1 號生產者 AI。
    請針對以下單字產出適合 {target_age} 歲（6-10歲區間）理解的內容。
    
    規格要求：
    1. 每一行一個單字，欄位間用 "|" 分隔。
    2. 欄位順序：age|word|category|prefix|root|suffix|phonetic|visual_vibe|field_app
    3. visual_vibe: 必須使用具體動作或畫面（例如：串珍珠、傳聲筒）。
    4. field_app: 說明這個字在該領域怎麼「動」起來的。
    
    單字清單：{", ".join(words_list)}
    """
    
    # 調用 Gemini 執行
    response = client.models.generate_content(model="gemini-3.0-flash", contents=mass_prompt)
    return response.text

# --- 3. 介面：協作量產區 ---
if menu == "🏭 9欄位量產":
    st.header("🛠 Kadowsella 全齡量產模式")
    
    # 選擇目標年齡層 (x+5 邏輯)
    target_age = st.selectbox("目標年齡層 (x 歲)", [i for i in range(0, 101, 5)], index=2) # 預設 10 歲
    
    input_words = st.text_area("請輸入想產出的單字 (用逗號隔開)", "API, Cloud, Encryption")
    
    if st.button("🚀 執行量產流程"):
        words = [w.strip() for w in input_words.split(",")]
        
        with st.spinner(f"正在為 {len(words)} 個單字打造 {target_age} 歲階梯..."):
            raw_result = generate_kadowsella_data(words, target_age)
            
            # 解析 AI 回傳
            new_rows = []
            for line in raw_result.strip().split('\n'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == 9:
                    new_rows.append(parts)
            
            # 轉成 DataFrame 預覽
            new_df = pd.DataFrame(new_rows, columns=COL_NAMES_9)
            st.write("🎉 生產完畢！預覽如下：")
            st.dataframe(new_df)
            
            # 暫存在 session_state 準備同步
            if 'temp_db' not in st.session_state:
                st.session_state.temp_db = new_df
            else:
                st.session_state.temp_db = pd.concat([st.session_state.temp_db, new_df])
