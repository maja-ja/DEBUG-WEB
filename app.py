import streamlit as st
import pandas as pd
from google import genai
import re
from streamlit_gsheets import GSheetsConnection

# --- 0. 頁面配置 ---
st.set_page_config(page_title="Etymon AI Admin 2026", layout="wide")

# --- 1. 初始化新版 Gemini SDK ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = "gemini-2.5-flash" 
except Exception as e:
    st.error(f"AI 初始化失敗，請檢查 Secret: {e}")

# --- 2. 輔助函數 ---
def heavy_clean(text):
    if not text: return ""
    return re.sub(r'\s+', '', str(text)).lower().strip()

# --- 3. 雲端連線與資料初始化 ---
conn = st.connection("gsheets", type=GSheetsConnection)
NEW_DB_URL = "https://docs.google.com/spreadsheets/d/1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg/edit?gid=204425767#gid=204425767"

if 'db' not in st.session_state:
    try:
        df = conn.read(spreadsheet=NEW_DB_URL, ttl=0)
        df.columns = [str(c).strip().lower() for c in df.columns]
        st.session_state.db = df.dropna(subset=['word']).reset_index(drop=True)
    except:
        st.session_state.db = pd.DataFrame(columns=['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation','native_vibe'])

# --- 4. 側邊欄導航系統 (解決跳頁問題的核心) ---
with st.sidebar:
    st.title("🚀 Etymon AI 終端")
    st.markdown("---")
    # 使用 radio 作為導航，key 確保狀態持久化
    menu = st.radio(
        "功能選單",
        ["✨ 批次生成", "🧹 庫管理", "☁️ 雲端同步", "🔄 批次重整", "🧠 語感校驗"],
        key="main_nav"
    )
    st.markdown("---")
    st.metric("當前資料庫筆數", len(st.session_state.db))
    if st.button("♻️ 強制重新讀取雲端"):
        del st.session_state.db
        st.rerun()

# --- 5. 各頁面邏輯 ---

# --- 頁面 A: AI 生成 ---
if menu == "✨ 批次生成":
    st.header("✨ 批次單字生成")
    topic = st.text_input("輸入主題 (例如：高中必備 re- 字首)：", placeholder="請輸入主題...")
    num_count = st.slider("選擇生成數量", 20, 100, 30)
    
    if st.button(f"🪄 使用 {MODEL_ID} 開始生成"):
        with st.spinner("AI 正在思考中..."):
            try:
                prompt = f"""請生成 {num_count} 個關於「{topic}」的英文單字。格式：category|roots|meaning|word|breakdown|definition|phonetic|example|translation|native_vibe(不要標題，不要說明，category｜meaning｜definition｜translation，都是繁體中文，而且translation是example的翻譯。native_vibe可以以以下格式輸出：
                你是語言直覺大師。請為以下單字提供『母語人士語感 (Native Vibe)』。
                要求：
                1. 語感必須包含：視覺/聽覺意象、社會階層感、或一個毒舌的生活化造句。
                2. 格式：單字 | 語感內容 (每個單字一行)
                3. 語言：繁體中文，幽默精闢。
                4. 請讓語感分析充滿驚喜感。開頭可以先否定課本定義，例如：『雖然字典說它是精密的，但在紐約華爾街，這聽起來更像是...』，讓解鎖的人覺得賺到了。)"""
                
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                lines = [l.strip().split('|') for l in response.text.strip().split('\n') if len(l.split('|')) == 10]
                
                if lines:
                    st.session_state.ai_draft = pd.DataFrame(lines, columns=st.session_state.db.columns)
                    st.success(f"成功生成 {len(lines)} 筆資料！")
                else:
                    st.error("格式不符，請重試。")
            except Exception as e:
                st.error(f"錯誤：{e}")

    if 'ai_draft' in st.session_state:
        st.divider()
        st.markdown("### 📝 預覽與匯入")
        draft_df = st.session_state.ai_draft.copy()
        if "核可" not in draft_df.columns: draft_df.insert(0, "核可", True)
        edited_df = st.data_editor(draft_df, key="vocal_editor", hide_index=True)
        
        if st.button("📥 匯入選中單字到暫存庫", use_container_width=True):
            to_add = edited_df[edited_df['核可'] == True].drop(columns=['核可'])
            st.session_state.db = pd.concat([st.session_state.db, to_add], ignore_index=True)
            del st.session_state.ai_draft
            st.success("匯入成功！")
            st.rerun()
# --- 頁面 B: 庫管理 (修正變數報錯版) ---
elif menu == "🧹 庫管理":
    st.header("🧹 資料庫健康檢查")
    
    if not st.session_state.db.empty:
        # 1. 務必先計算 duplicates，再進入 if 判斷
        temp_df = st.session_state.db.copy()
        
        # 建立去重用 key
        temp_df['match_key'] = (
            temp_df['word'].apply(heavy_clean) + "|" + 
            temp_df['category'].apply(heavy_clean)
        )
        
        # 找出重複項
        duplicates = temp_df[temp_df.duplicated(subset=['match_key'], keep='first')]
        
        # 2. 顯示統計數據
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("總筆數", len(temp_df))
        col_m2.metric("重複項目", len(duplicates))

        # 3. 處理重複項的 UI
        if not duplicates.empty:
            with st.expander("查看重複的項目內容"):
                st.write(duplicates[['word', 'category', 'definition']])
            
            if st.button("🔥 立即移除重複並同步至雲端", use_container_width=True):
                # 執行去重
                cleaned_df = temp_df.drop_duplicates(subset=['match_key'], keep='first').drop(columns=['match_key'])
                st.session_state.db = cleaned_df
                
                # 同步到 Google Sheets
                with st.spinner("同步至雲端中..."):
                    conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
                st.success("重複項已移除並同步雲端！")
                st.rerun()
        else:
            st.success("✨ 資料庫狀態良好，無重複項。")

        st.divider()
        st.subheader("🗑️ 手動編輯庫存")
        st.info("💡 刪除行後，請務必點擊下方的『同步到雲端』按鈕。")

        # 4. 手動編輯區
        edited_db = st.data_editor(
            st.session_state.db, 
            key="main_db_editor_v3", 
            num_rows="dynamic",
            use_container_width=True
        )
        
        if st.button("💾 保存編輯並同步到雲端", type="primary", use_container_width=True):
            st.session_state.db = edited_db
            with st.spinner("正在將手動修改寫入雲端..."):
                conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
            st.success("修改已成功保存至 Google Sheets！")
            st.rerun()
            
    else:
        st.info("資料庫目前是空的，請先去『✨ 批次生成』。")

# --- 頁面 C: 雲端同步 ---
elif menu == "☁️ 雲端同步":
    st.header("☁️ 同步至 Google Sheets")
    st.warning("提醒：這會覆蓋雲端試算表上的所有舊資料。")
    st.dataframe(st.session_state.db, use_container_width=True)
    
    if st.button("💾 執行寫入雲端", type="primary", use_container_width=True):
        with st.spinner("同步中..."):
            conn.update(spreadsheet=NEW_DB_URL, data=st.session_state.db)
            st.success("🎉 同步成功！")
            st.balloons()

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
                    refactor_prompt = f"請將以下單字重新整理成 10 欄位 CSV 格式 (| 分隔格式：category|roots|meaning|word|breakdown|definition|phonetic|example|translation|native_vibe(不要標題，不要說明，category｜meaning｜definition｜translation，都是繁體中文，而且translation是example的翻譯。native_vibe可以無視
)，確保內容為繁體中文：{word_list}"
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
                你是語言直覺大師。請為以下單字提供『母語人士語感 (Native Vibe)』。
                要求：
                1. 語感必須包含：視覺/聽覺意象、社會階層感、或一個毒舌的生活化造句。
                2. 格式：單字 | 語感內容 (每個單字一行)
                3. 語言：繁體中文，幽默精闢。
                4. 請讓語感分析充滿驚喜感。開頭可以先否定課本定義，例如：『雖然字典說它是精密的，但在紐約華爾街，這聽起來更像是...』，讓解鎖的人覺得賺到了。
                
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
