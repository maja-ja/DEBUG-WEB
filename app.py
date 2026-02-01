# --- 2. 核心量產指令 (1號生產者 + 2號校對者邏輯) ---
def generate_kadowsella_data(words_list, target_age):
    # 這裡確保使用正確的 Model ID
    mass_prompt = f"""
    你現在是 Kadowsella 開源計畫的執行專家。
    請針對單字清單：{", ".join(words_list)}
    產出適合「{target_age} 歲」理解的專業內容。
    
    格式規範（極度重要）：
    1. 輸出必須純粹是資料行，不准有 Markdown 標題、不准有說明文字、不准有開頭結尾。
    2. 每一行代表一個單字，欄位間嚴格使用「|」隔開。
    3. 欄位順序必須是：age|word|category|prefix|root|suffix|phonetic|visual_vibe|field_app
    4. 語言：必須使用繁體中文。
    5. 解釋風格：
       - visual_vibe: 給 6-10 歲孩子的具體畫面（例如：API 像服務生送菜）。
       - field_app: 解釋在專業領域（如資工、醫學）的具體用途。
    """
    
    try:
        # 使用你定義過的 client 物件
        response = client.models.generate_content(model="gemini-2.0-flash", contents=mass_prompt)
        return response.text
    except Exception as e:
        return f"ERROR|{e}"

# --- 3. 介面：協作量產區 ---
if menu == "🏭 9欄位量產":
    st.header("🛠 Kadowsella 全齡量產模式 (9欄位)")
    
    target_age = st.selectbox("目標年齡層 (x 歲)", [i for i in range(0, 101, 5)], index=2)
    input_words = st.text_area("請輸入單字 (用逗號隔開)", "Database, Cache, Firewall")
    
    if st.button("🚀 第一、二、三個人開始工作！"):
        # 1. 清理輸入資料
        words = [w.strip() for w in input_words.split(",") if w.strip()]
        
        if not words:
            st.warning("請輸入至少一個單字。")
        else:
            with st.spinner(f"正在織網中... 產出 {target_age} 歲的解釋"):
                raw_result = generate_kadowsella_data(words, target_age)
                
                # 2. 精準解析 AI 回傳
                new_rows = []
                # 這裡增加檢查過濾，避免空行與錯誤
                for line in raw_result.strip().split('\n'):
                    if "|" in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) == 9:
                            new_rows.append(parts)
                
                if new_rows:
                    new_df = pd.DataFrame(new_rows, columns=COL_NAMES_9)
                    st.success(f"🎉 產出成功！共 {len(new_df)} 筆。")
                    
                    # 3. 提供編輯器（讓你在存檔前做最後微調）
                    edited_df = st.data_editor(new_df, use_container_width=True)
                    
                    # 暫存在 session_state
                    if 'temp_db' not in st.session_state:
                        st.session_state.temp_db = edited_df
                    else:
                        st.session_state.temp_db = pd.concat([st.session_state.temp_db, edited_df]).drop_duplicates(subset=['word', 'age'])
                    
                    st.info("💡 資料已進入待傳送緩存。請前往『☁️ 雲端同步』執行寫回。")
                else:
                    st.error("AI 回傳格式不正確，請再試一次。")
                    st.code(raw_result) # 顯示原始結果方便 Debug
