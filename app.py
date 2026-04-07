import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re
import os
import onnxruntime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# =========================
# 1️⃣ 懶載入 ONNX 模型
# =========================
@st.cache_resource
def load_onnx_model():
    st.info("正在載入 ONNX 模型，請稍候...")
    tokenizer = SentenceTransformer('paraphrase-MiniLM-L3-v2').tokenizer
    session = onnxruntime.InferenceSession("MiniLM-L3-onnx/model.onnx")
    st.success("模型載入完成 ✅")
    return tokenizer, session

model_loaded = False
tokenizer, session = None, None

# =========================
# 2️⃣ 文字編碼函數（批次處理）
# =========================
def encode_onnx(texts, batch_size=5):
    global tokenizer, session, model_loaded
    if not model_loaded:
        tokenizer, session = load_onnx_model()
        model_loaded = True
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

# =========================
# 3️⃣ Session 初始化
# =========================
if "data" not in st.session_state:
    st.session_state.data = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "keyword" not in st.session_state:
    st.session_state.keyword = ""

# =========================
# 4️⃣ 工具函數
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

def semantic_score(query, text):
    q_vec = encode_onnx(query)
    t_vec = encode_onnx(text)
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

# =========================
# 5️⃣ PTT 搜尋
# =========================
def fetch_ptt(keyword, limit=10, max_pages=20):
    st.info("正在搜尋 PTT...")
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

    for page_num in range(max_index, max_index - max_pages, -1):
        if page_num <= 0:
            break
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
# 6️⃣ 新聞 RSS 搜尋
# =========================
def fetch_news(keyword, limit=10):
    st.info("正在搜尋新聞...")
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []
    keywords = get_keywords(keyword)
    try:
        feed = feedparser.parse(RSS_URL)
    except:
        return []

    for entry in feed.entries:
        title = BeautifulSoup(entry.title, "html.parser").text
        link = entry.link
        score = compute_score(title, keywords)
        if score >= 2:
            articles.append({"title": title, "link": link, "score": score, "source": "新聞"})

    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# =========================
# 7️⃣ UI
# =========================
st.title("🔍 智能搜尋器 Pro")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

source = st.radio("資料來源", ["PTT", "新聞", "全部"])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋 + AI分析中..."):
        data = []
        if source in ["PTT", "全部"]:
            data += fetch_ptt(keyword, limit)
        if source in ["新聞", "全部"]:
            data += fetch_news(keyword, limit)
        data.sort(key=lambda x: x["score"], reverse=True)
        st.session_state.data = data
        st.session_state.keyword = keyword
        st.session_state.searched = True

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

# =========================
# 8️⃣ Render Port 設定
# =========================
# Streamlit 會自動用 Render 提供的 $PORT
port = int(os.environ.get("PORT", 8501))
st.write(f"應用正在運行在 port {port}")