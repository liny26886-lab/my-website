import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re
import os
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# =========================
# 1️⃣ Render Port 設定
# =========================
port = int(os.environ.get("PORT", 8501))
st.set_page_config(page_title="智能搜尋器 Pro", layout="wide")

# =========================
# 2️⃣ Session 初始化
# =========================
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False
if "model" not in st.session_state:
    st.session_state.model = None
if "data" not in st.session_state:
    st.session_state.data = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "keyword" not in st.session_state:
    st.session_state.keyword = ""

# =========================
# 3️⃣ 工具函數
# =========================
def get_keywords(keyword):
    return [k for k in re.split(r"\s+", keyword) if k]

def highlight(text, keyword):
    if not text or not keyword:
        return text
    try:
        return re.sub(
            f"({'|'.join(map(re.escape, keyword.split()))})",
            r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
            text,
            flags=re.IGNORECASE
        )
    except:
        return text

# =========================
# 4️⃣ ONNX 推理函數（依賴延遲 import）
# =========================
def encode_onnx(texts, tokenizer, session, batch_size=5):
    if isinstance(texts, str):
        texts = [texts]
    embeddings_list = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, return_tensors="np")
        allowed_keys = {inp.name for inp in session.get_inputs()}
        ort_inputs = {k: v for k, v in inputs.items() if k in allowed_keys}
        ort_outs = session.run(None, ort_inputs)
        embeddings_list.extend(ort_outs[0])
    return np.array(embeddings_list)

def semantic_score(query, text):
    tokenizer, session = st.session_state.model['tokenizer'], st.session_state.model['session']
    q_vec = encode_onnx(query, tokenizer, session)
    t_vec = encode_onnx(text, tokenizer, session)
    return float(cosine_similarity(q_vec, t_vec)[0][0])

def keyword_score(text, keywords):
    text = text.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in text:
            score += 3
    return score

def compute_score(text, keywords):
    sem = semantic_score(st.session_state.keyword, text)
    key = keyword_score(text, keywords)
    return sem * 0.7 + key * 0.3

# 5️⃣ 模型載入（延遲 import）
# =========================
def load_model_with_progress(overall_progress):
    import onnxruntime
    from transformers import AutoTokenizer
    import time

    model_dict = {}

    # Step 1: 初始化 tokenizer
    overall_progress.text("Step 1/3: 初始化 tokenizer …")
    time.sleep(0.2)
    tokenizer = AutoTokenizer.from_pretrained("./model")  # 只載入 tokenizer
    model_dict['tokenizer'] = tokenizer
    overall_progress.progress(10)

    # Step 2: 初始化 ONNX session
    overall_progress.text("Step 2/3: 初始化 ONNX session …")
    time.sleep(0.2)
    session = onnxruntime.InferenceSession("model.onnx")
    model_dict['session'] = session
    overall_progress.progress(50)

    # Step 3: 模型載入完成
    overall_progress.text("Step 3/3: 模型載入完成 ✅")
    time.sleep(0.2)
    overall_progress.progress(100)
    import streamlit as st
    st.success("模型成功載入 ✅")

    return model_dict

# =========================
# 6️⃣ PTT 搜尋
# =========================
def fetch_ptt(keyword, limit=10, max_pages=5, overall_progress=None):
    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}
    keywords = get_keywords(keyword)
    articles = []

    try:
        res = requests.get(f"{PTT_URL}/bbs/Gossiping/index.html", headers=headers, cookies=cookies, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        btn = soup.select("a.btn.wide")
        max_index = 0
        for b in btn:
            if "上頁" in b.text:
                match = re.search(r"index(\d+).html", b["href"])
                if match:
                    max_index = int(match.group(1)) + 1
                    break
    except:
        return []

    for i, page_num in enumerate(range(max_index, max_index - max_pages, -1), start=1):
        if page_num <= 0:
            break
        if overall_progress:
            overall_progress.text(f"抓取 PTT 第 {i}/{max_pages} 頁 …")
            overall_progress.progress(10 + int(i/max_pages*30))
        try:
            res = requests.get(f"{PTT_URL}/bbs/Gossiping/index{page_num}.html",
                               headers=headers, cookies=cookies, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.select(".r-ent .title a"):
                title = a.text.strip()
                link = PTT_URL + a["href"]
                score = compute_score(title, keywords)
                if score >= 2:
                    articles.append({"title": title, "link": link, "score": score, "source": "PTT"})
        except:
            continue
    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# =========================
# 7️⃣ 新聞 RSS 搜尋
# =========================
def fetch_news(keyword, limit=10, overall_progress=None):
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []
    keywords = get_keywords(keyword)
    try:
        feed = feedparser.parse(RSS_URL)
    except:
        return []

    total_entries = len(feed.entries)
    for i, entry in enumerate(feed.entries, start=1):
        if overall_progress:
            overall_progress.text(f"抓取新聞 {i}/{total_entries} …")
            overall_progress.progress(40 + int(i/total_entries*60))
        title = BeautifulSoup(entry.title, "html.parser").text
        link = entry.link
        score = compute_score(title, keywords)
        if score >= 2:
            articles.append({"title": title, "link": link, "score": score, "source": "新聞"})
    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# =========================
# 8️⃣ UI
# =========================
st.title("🔍 智能搜尋器 Pro (含整體進度條)")

col1, col2 = st.columns([3,1])
with col1:
    keyword_input = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

source = st.radio("資料來源", ["PTT", "新聞", "全部"])

overall_progress = st.empty()
progress_bar = st.progress(0)

# 模型載入按鈕（延遲 import）
if not st.session_state.model_loaded:
    if st.button("載入模型"):
        with st.spinner("模型載入中，請稍候..."):
            st.session_state.model = load_model_with_progress(overall_progress)
            st.session_state.model_loaded = True

# 搜尋按鈕
if st.session_state.model_loaded and st.button("開始搜尋 🔍") and keyword_input:
    st.session_state.keyword = keyword_input
    st.session_state.data = []
    st.session_state.searched = True

    with st.spinner("資料抓取中，請稍候..."):
        data = []
        if source in ["PTT", "全部"]:
            data += fetch_ptt(keyword_input, limit, overall_progress=overall_progress)
        if source in ["新聞", "全部"]:
            data += fetch_news(keyword_input, limit, overall_progress=overall_progress)
        data.sort(key=lambda x: x["score"], reverse=True)
        st.session_state.data = data

    overall_progress.text("全部抓取完成 ✅")
    progress_bar.progress(100)
    st.success("所有資料抓取完成 ✅")

# 顯示結果
if st.session_state.searched:
    if source == "PTT":
        show_data = [d for d in st.session_state.data if d["source"] == "PTT"]
    elif source == "新聞":
        show_data = [d for d in st.session_state.data if d["source"] == "新聞"]
    else:
        show_data = st.session_state.data

    st.write(f"共 {len(show_data)} 筆結果")
    for article in show_data:
        title = highlight(article["title"], st.session_state.keyword)
        st.markdown(f"""
        <div style="background:#1e1e1e;padding:15px;border-radius:10px;margin-bottom:10px;">
            <h4 style="color:white;">{title}</h4>
            <p style="color:gray;">相關度：{article['score']:.2f}</p>
            <a href="{article['link']}" target="_blank">查看文章</a>
        </div>
        """, unsafe_allow_html=True)