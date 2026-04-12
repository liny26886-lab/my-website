import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# =========================
# 1️⃣ 設定
# =========================
st.set_page_config(page_title="智能搜尋器 Pro", layout="wide")

progress_text = st.empty()
progress_bar = st.progress(0)

# =========================
# 2️⃣ Session
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
# 3️⃣ 工具
# =========================
def get_keywords(keyword):
    return [k for k in re.split(r"\s+", keyword) if k]

def keyword_score(text, keywords):
    text = text.lower()
    return sum(3 for kw in keywords if kw.lower() in text)

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
# 4️⃣ ONNX encode（修正版）
# =========================
def encode_onnx(texts, tokenizer, session, batch_size=8):
    if isinstance(texts, str):
        texts = [texts]

    embeddings_list = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        inputs = tokenizer(
            batch,
            padding="max_length",
            truncation=True,
            max_length=128,
            return_tensors="np"
        )

        inputs = {k: v.astype("int64") for k, v in inputs.items()}

        ort_inputs = {}
        for inp in session.get_inputs():
            if inp.name in inputs:
                ort_inputs[inp.name] = inputs[inp.name]

        ort_outs = session.run(None, ort_inputs)
        embeddings_list.append(ort_outs[0])

    return np.vstack(embeddings_list)

# =========================
# 5️⃣ scoring
# =========================
def compute_scores_batch(texts, keywords):
    tokenizer = st.session_state.model["tokenizer"]
    session = st.session_state.model["session"]

    q_vec = encode_onnx(st.session_state.keyword, tokenizer, session)
    t_vecs = encode_onnx(texts, tokenizer, session)

    scores = []
    for i, text in enumerate(texts):
        sem = cosine_similarity(q_vec, t_vecs[i].reshape(1, -1))[0][0]
        key = keyword_score(text, keywords)
        scores.append(sem * 0.7 + key * 0.3)

    return scores

# =========================
# 6️⃣ 模型載入（含進度）
# =========================
def load_model():
    import onnxruntime
    from transformers import AutoTokenizer

    progress_text.text("載入 tokenizer...")
    progress_bar.progress(20)
    tokenizer = AutoTokenizer.from_pretrained("./model")

    progress_text.text("載入 ONNX 模型...")
    progress_bar.progress(60)
    session = onnxruntime.InferenceSession("model.onnx")

    progress_text.text("模型載入完成")
    progress_bar.progress(100)

    return {"tokenizer": tokenizer, "session": session}

# =========================
# 7️⃣ PTT
# =========================
def fetch_ptt(keyword, limit=10, max_pages=3):
    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}

    keywords = get_keywords(keyword)
    articles = []

    try:
        res = requests.get(f"{PTT_URL}/bbs/Gossiping/index.html",
                           headers=headers, cookies=cookies)
        soup = BeautifulSoup(res.text, "html.parser")

        btn = soup.select("a.btn.wide")
        max_index = 0
        for b in btn:
            if "上頁" in b.text:
                m = re.search(r"index(\d+).html", b["href"])
                if m:
                    max_index = int(m.group(1)) + 1
                    break
    except:
        return []

    for i, page in enumerate(range(max_index, max_index-max_pages, -1), 1):

        progress_text.text(f"抓取 PTT 第 {i}/{max_pages} 頁")
        progress_bar.progress(int(i / max_pages * 50))

        try:
            res = requests.get(f"{PTT_URL}/bbs/Gossiping/index{page}.html",
                               headers=headers, cookies=cookies)
            soup = BeautifulSoup(res.text, "html.parser")

            titles, links = [], []

            for a in soup.select(".r-ent .title a"):
                titles.append(a.text.strip())
                links.append(PTT_URL + a["href"])

            if not titles:
                continue

            scores = compute_scores_batch(titles, keywords)

            for t, l, s in zip(titles, links, scores):
                if s >= 2:
                    articles.append({
                        "title": t,
                        "link": l,
                        "score": s,
                        "source": "PTT"
                    })

        except:
            continue

    return sorted(articles, key=lambda x: x["score"], reverse=True)[:limit]

# =========================
# 8️⃣ News
# =========================
def fetch_news(keyword, limit=10):
    RSS = "https://news.ltn.com.tw/rss/all.xml"
    keywords = get_keywords(keyword)

    feed = feedparser.parse(RSS)

    titles = [BeautifulSoup(e.title, "html.parser").text for e in feed.entries]
    links = [e.link for e in feed.entries]

    scores = compute_scores_batch(titles, keywords)

    articles = []

    for i, (t, l, s) in enumerate(zip(titles, links, scores), 1):

        progress_text.text(f"分析新聞 {i}/{len(titles)}")
        progress_bar.progress(50 + int(i / len(titles) * 50))

        if s >= 2:
            articles.append({
                "title": t,
                "link": l,
                "score": s,
                "source": "新聞"
            })

    return sorted(articles, key=lambda x: x["score"], reverse=True)[:limit]

# =========================
# 9️⃣ UI
# =========================
st.title("🔍 智能搜尋器 Pro（穩定版）")

col1, col2 = st.columns([3, 1])

with col1:
    keyword_input = st.text_input("輸入關鍵字", value=st.session_state.keyword)

with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

source = st.radio("資料來源", ["PTT", "新聞", "全部"])

# load model
if not st.session_state.model_loaded:
    if st.button("載入模型"):
        st.session_state.model = load_model()
        st.session_state.model_loaded = True
        st.success("模型載入完成")

# search
if st.session_state.model_loaded and st.button("開始搜尋"):
    st.session_state.keyword = keyword_input

    data = []

    if source in ["PTT", "全部"]:
        data += fetch_ptt(keyword_input, limit)

    if source in ["新聞", "全部"]:
        data += fetch_news(keyword_input, limit)

    st.session_state.data = sorted(data, key=lambda x: x["score"], reverse=True)
    st.session_state.searched = True

    progress_text.text("完成")
    progress_bar.progress(100)

# show
if st.session_state.searched:
    st.write(f"共 {len(st.session_state.data)} 筆結果")

    for a in st.session_state.data:
        title = highlight(a["title"], st.session_state.keyword)

        st.markdown(f"""
        <div style="background:#1e1e1e;padding:15px;border-radius:10px;margin-bottom:10px;">
            <h4 style="color:white;">{title}</h4>
            <p style="color:gray;">相關度：{a['score']:.2f}</p>
            <a href="{a['link']}" target="_blank">查看</a>
        </div>
        """, unsafe_allow_html=True)