import streamlit as st
import pandas as pd
from google import genai
import re
import time
from streamlit_gsheets import GSheetsConnection

# --- 0. 頁面配置 ---
st.set_page_config(page_title="Etymon AI Admin 2026 (20-Col Edition)", layout="wide")

# --- 1. 核心欄位與配置 ---
COL_NAMES_20 = [
    'category', 'roots', 'meaning', 'word', 'breakdown', 
    'definition', 'phonetic', 'example', 'translation', 'native_vibe',
    'synonym_nuance', 'visual_prompt', 'social_status', 'emotional_tone', 'street_usage',
    'collocation', 'etymon_story', 'usage_warning', 'memory_hook', 'audio_tag'
]

# --- 2. 初始化 Gemini ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.0-flash" 
except Exception as e:
    st.error(f"AI 初始化失敗: {e}")

# --- 3. 雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)
NEW_DB_URL = "https://docs.google.com/spreadsheets/d/1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg/edit?gid=204425767#gid=204425767"

if 'db' not in st.session_state:
    try:
        df = conn.read(spreadsheet=NEW_DB_URL, ttl=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        # 確保所有 20 欄都存在於 dataframe 中
        for col in COL_NAMES_20:
            if col not in df.columns:
                df[col] = ""
        st.session_state.db = df.dropna(subset=['word']).reset_index(drop=True)
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
        st.session_state.db = pd.DataFrame(columns=COL_NAMES_20)

# --- 4. 介面設計 ---
st.title("🧩 Etymon 語感百科：20 欄位全自動管理端")

menu = st.sidebar.selectbox("功能選單", ["📊 資料總覽", "🏭 協作量產 (20欄)", "☁️ 雲端同步"])

# --- 功能：資料總覽 ---
if menu == "📊 資料總覽":
    st.write(f"當前資料筆數：{len(st.session_state.db)}")
    st.dataframe(st.session_state.db)

# --- 功能：協作量產 (重點升級) ---
elif menu == "🏭 協作量產 (20欄)":
    st.header("🛠 多人協作量產模式")
    st.info("請同學分配好各自的區間（例如：A 處理 0-100，B 處理 101-200），避免同時存取。")
    
    col1, col2 = st.columns(2)
    with col1:
        start_idx = st.number_input("起始索引 (Index Start)", value=0, min_value=0, step=10)
    with col2:
        end_idx = st.number_input("結束索引 (Index End)", value=min(start_idx + 10, len(st.session_state.db)), min_value=0)

    target_words = st.session_state.db.iloc[start_idx:end_idx]
    st.write("📍 待處理單字：", ", ".join(target_words['word'].tolist()))

    if st.button("🚀 執行 AI 深度消化 (20 欄)"):
        if target_words.empty:
            st.warning("請選擇有效的索引區間")
        else:
            progress_bar = st.progress(0)
            words_string = ", ".join(target_words['word'].tolist())
            
            # 終極 Prompt
            mass_prompt = f"""
你現在是一位精通字源學、語言心理學且語氣幽默的英語專家。
請針對以下單字進行「百科級」的解構，並嚴格遵守格式規範：

### 1. 輸出格式
每個單字請輸出為一行，欄位間用「|」隔開：
單字 | category | roots | meaning | breakdown | definition | example | translation

### 2. 欄位細節要求
- category: 該單字所屬的學科或語境 (中文)。
- roots: 核心字根。
- meaning: 字根的中文含義。
- breakdown: 【重要】中英混雜格式。範例：'geno (基因) + type (型)' 或 'optim (優) + ization (行為)'。
- definition: 精簡的中文核心定義。
- example: 一句道地的英文例句。
- translation: 例句的中文翻譯 (請充滿生活感)。

### 3. 範例 (請模仿此風格)
genotype | 生物學 | gen | 產生 | geno (基因) + type (型) | 基因型 | Genotype vs Phenotype. | 基因型與表型的對決。

單字清單：{words_string}
"""
            
            try:
                with st.spinner("AI 正在織網中..."):
                    response = client.models.generate_content(model=MODEL_ID, contents=mass_prompt)
                    lines = response.text.strip().split('\n')
                
                success_count = 0
                for line in lines:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:  # 至少要有單字本人
                        # 找尋 word 欄位匹配 (在第 4 欄，Index 3)
                        w_key = parts[3].lower()
                        row_idx = st.session_state.db[st.session_state.db['word'].str.lower() == w_key].index
                        
                        if not row_idx.empty:
                            # 填入 20 欄，若 AI 輸出不足則補空
                            for i, col in enumerate(COL_NAMES_20):
                                if i < len(parts):
                                    st.session_state.db.loc[row_idx, col] = parts[i]
                            success_count += 1
                
                st.success(f"✅ 完成 {success_count} 筆單字的深度重整！")
                st.balloons()
                st.dataframe(st.session_state.db.iloc[start_idx:end_idx])
                st.info("💡 提醒：處理完後請至『☁️ 雲端同步』寫回 Google Sheet。")
                
            except Exception as e:
                st.error(f"AI 產出發生錯誤: {e}")

# --- 功能：雲端同步 ---
elif menu == "☁️ 雲端同步":
    st.header("💾 同步至 Google Sheets")
    st.warning("同步將覆蓋雲端現有的",f"{len(st.session_state.db)}", " 筆資料，請確認欄位數為 20 欄。")
    
    if st.button("確認同步寫回雲端"):
        try:
            with st.spinner("正在同步..."):
                # 這裡會根據 st.session_state.db 的欄位順序寫回
                conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
                st.success("✅ 雲端資料庫已更新！")
        except Exception as e:
            st.error(f"同步失敗: {e}")
# --- 頁面 D: 批次重整 ---
elif menu == "🔄 批次重整":
    st.header("🔄 資料重整流水線")
    if not st.session_state.db.empty:
        batch_size = 10
        total_records = len(st.session_state.db)
        total_batches = (total_records // batch_size) + (1 if total_records % batch_size > 0 else 0)
        
        batch_idx = st.number_input(f"選擇重整批次 (1-{total_batches})", 1, total_batches, 1)
        safe_start = (batch_idx - 1) * batch_size
        safe_end = min(safe_start + batch_size, total_records)
        
        st.info(f"正在選取：第 {safe_start+1} 到 {safe_end} 筆資料")
        current_batch = st.session_state.db.iloc[safe_start:safe_end]

        if st.button(f"🚀 AI 重新審核第 {batch_idx} 批"):
            with st.spinner("AI 處理中..."):
                try:
                    word_list = ", ".join(current_batch['word'].tolist())
                    refactor_prompt = f"""請將以下單字重新整理成 10 欄位 CSV 格式 (| 分隔格式：category|roots|meaning|word|breakdown|definition|phonetic|example|translation|native_vibe(不要標題，不要說明，category｜meaning｜definition｜translation，都是繁體中文，而且translation是example的翻譯。native_vibe可以無視
)，確保內容為繁體中文：{word_list}"""
                    response = client.models.generate_content(model=MODEL_ID, contents=refactor_prompt)
                    lines = [l.strip().split('|') for l in response.text.strip().split('\n') if len(l.split('|')) == 9]
                    if lines:
                        st.session_state.refactor_draft = pd.DataFrame(lines, columns=st.session_state.db.columns)
                        st.success("預覽已生成！")
                    else:
                        st.error("回傳格式異常。")
                except Exception as e:
                    st.error(f"API 錯誤：{e}")

        if 'refactor_draft' in st.session_state:
            st.divider()
            edited_refactor = st.data_editor(st.session_state.refactor_draft, key=f"ref_edit_{batch_idx}")
            if st.button("✅ 確認覆蓋舊資料並更新"):
                to_drop = st.session_state.db.index[safe_start:safe_end]
                remaining_db = st.session_state.db.drop(to_drop)
                st.session_state.db = pd.concat([remaining_db, edited_refactor], ignore_index=True)
                del st.session_state.refactor_draft
                st.success("更新成功！")
                st.rerun()
    else:
        st.info("暫存庫為空。")
# --- 頁面 E: 母語語感校驗 (考卷模式) ---

elif menu == "🧠 語感校驗":
    st.header("🧠 母語人士直覺壓力測試")
    st.info("這份考卷不是考你，是考 AI 對你資料庫單字的『理解深度』。")

    if not st.session_state.db.empty:
        # 1. 抽樣與準備
        if st.button("🎲 隨機抽取單字並生成考卷"):
            sample_row = st.session_state.db.sample(1).iloc[0]
            st.session_state.exam_target = sample_row.to_dict()
            st.session_state.pop('exam_result', None) # 清除舊結果

        if 'exam_target' in st.session_state:
            target = st.session_state.exam_target
            st.subheader(f"當前測試目標：**{target['word']}**")
            st.caption(f"原始定義：{target['definition']} | 字根：{target['roots']}")

            if st.button("🚀 開始校驗 (AI 深度分析)"):
                with st.spinner("正在模擬母語人士腦迴路..."):
                    exam_prompt = f"""
                    你現在是一位具備深厚語言學背景的美國母語人士。
                    請針對單字 '{target['word']}' 進行以下層次的說明，純中文文本，不可出現markdown、表情符號：
                    
                    1. 如果不看字典，這個字給人的顏色、溫度、或社會階層感是什麼？(例如：它聽起來像穿西裝的人說的，還是滑板少年說的？)
                    2. 如果有給出一個極其日常、甚至帶點諷刺或情緒化的句子，這是在課本上絕對學不到的用法。
                    
                    
                    請用繁體中文回答，並保持幽默、精闢、不說廢話。
                    """
                    try:
                        response = client.models.generate_content(model=MODEL_ID, contents=exam_prompt)
                        st.session_state.exam_result = response.text
                    except Exception as e:
                        st.error(f"分析失敗：{e}")

            
            # 顯示結果
            if 'exam_result' in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state.exam_result)
                
                if 'exam_result' in st.session_state:
                    # --- 在「語感回流」區塊更新如下 ---
                    st.divider()
                    st.subheader("📥 語感回流")
                    if st.button("💾 永久記錄此語感至資料庫"):
                        # 找到目前單字在 DataFrame 中的索引
                        idx = st.session_state.db[st.session_state.db['word'] == target['word']].index
                        
                        if not idx.empty:
                            # 將 AI 分析結果寫入該列的 'native_vibe' 欄位
                            st.session_state.db.loc[idx, 'native_vibe'] = st.session_state.exam_result
                            st.success(f"✅ '{target['word']}' 的語感已存入暫存！")
                            st.info("💡 記得去『☁️ 雲端同步』頁面執行『寫入雲端』，才會永久保存到 Google Sheets 喔！")
    else:
        st.warning("資料庫空空的，沒辦法出題喔！")
elif menu == "🏭 語感量產":
    st.header("🏭 語感自動化生產線")
    
    # 1. 找出還沒有語感的單字
    empty_vibe_df = st.session_state.db[
        (st.session_state.db['native_vibe'].isna()) | 
        (st.session_state.db['native_vibe'] == "")
    ]
    
    st.metric("待處理單字量", len(empty_vibe_df))

    if not empty_vibe_df.empty:
        batch_size = st.slider("每批生產數量", 5, 30, 20)
        
        if st.button(f"🚀 開始量產前 {batch_size} 筆語感"):
            batch_words = empty_vibe_df.head(batch_size)['word'].tolist()
            words_string = ", ".join(batch_words)
            
            with st.spinner(f"正在為 {len(batch_words)} 個單字注入靈魂..."):
                mass_prompt = f"""
你是一位擁有極致語感、毒舌且幽默的英語語言學家。請針對以下單字清單，產出 20 欄位的完整描述。
格式要求：
1. 每一行代表一個單字。
2. 每個欄位之間使用 "|" 分隔。
3. 20 個欄位的標頭順序為：
   category | roots | meaning | word | breakdown | definition | phonetic | example | translation | native_vibe | synonym_nuance | visual_prompt | social_status | emotional_tone | street_usage | collocation | etymon_story | usage_warning | memory_hook | audio_tag

風格指引：
- native_vibe: 要有氣味、顏色、溫度與職業感。
- street_usage: 產出一個讓人噴飯、帶點諷刺的生活化情境。
- memory_hook: 越怪誕越好。

單字清單：{words_string}
"""
                
                try:
                    response = client.models.generate_content(model=MODEL_ID, contents=mass_prompt)
                    lines = response.text.strip().split('\n')
                    
                    # 2. 解析並回填
                    success_count = 0
                    for line in lines:
                        if "|" in line:
                            w, vibe = line.split("|", 1)
                            w = w.strip()
                            # 模糊匹配確保填入正確位置
                            idx = st.session_state.db[st.session_state.db['word'].str.lower() == w.lower()].index
                            if not idx.empty:
                                st.session_state.db.loc[idx, 'native_vibe'] = vibe.strip()
                                success_count += 1
                    
                    st.success(f"🎉 成功量產 {success_count} 筆語感資料！")
                    st.info("💡 請前往『☁️ 雲端同步』存檔。")
                    st.dataframe(st.session_state.db.loc[st.session_state.db['word'].isin(batch_words), ['word', 'native_vibe']])
                    
                except Exception as e:
                    st.error(f"量產中斷：{e}")
    else:
        st.balloons()
        st.success("所有單字都已經擁有靈魂了！")
