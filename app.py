import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
# ===== 1️⃣ 載入語意模型 =====
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')
model = load_model()
# ===== 2️⃣ Session 初始化 =====
if "data" not in st.session_state:
    st.session_state.data = []           # 存搜尋結果
if "searched" not in st.session_state:
    st.session_state.searched = False    # 是否已搜尋
if "keyword" not in st.session_state:
    st.session_state.keyword = ""        # 記錄搜尋字
# ===== 3️⃣ 工具函數 =====
# 拆關鍵字
def get_keywords(keyword):
    return [k for k in re.split(r"\s+", keyword) if k]
# 高亮文字
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
# 語意分數
def semantic_score(query_emb, text):
    text_emb = model.encode(text)
    return float(util.cos_sim(query_emb, text_emb))
# 關鍵字分數
def keyword_score(text, keywords):
    text = text.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in text:
            score += 3
    return score
# 免費摘要 (TF-IDF)
def extract_summary(text, n=2):
    sentences = re.split(r'[。！？]', text)
    sentences = [s for s in sentences if len(s.strip()) > 5]  # 避免空句
    if len(sentences) <= n:
        return text
    try:
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(sentences)
        scores = X.sum(axis=1)
        ranked = sorted(
            ((scores[i, 0], s) for i, s in enumerate(sentences)),
            reverse=True
        )
        summary = "。".join([s for _, s in ranked[:n]])
        return summary
    except:
        return text[:100]
# ===== 4️⃣ PTT 搜尋 =====
def fetch_ptt(keyword, limit=10, max_pages=20):
    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}
    keywords = get_keywords(keyword)
    articles = []
    # 找最新頁碼
    try:
        res = requests.get(f"{PTT_URL}/bbs/Gossiping/index.html", headers=headers, cookies=cookies)
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
    # 翻頁抓文章
    for page_num in range(max_index, max_index - max_pages, -1):
        if page_num <= 0:
            break
        try:
            res = requests.get(f"{PTT_URL}/bbs/Gossiping/index{page_num}.html",
                               headers=headers, cookies=cookies)
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.select(".r-ent .title a"):
                title = a.text.strip()
                link = PTT_URL + a["href"]
                score = compute_score(title, keywords)
                if score >= 2:   # 過濾低相關
                    articles.append({"title": title, "link": link, "score": score, "source": "PTT"})
        except:
            continue
    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]
# ===== 5️⃣ 新聞 RSS 搜尋 =====
def fetch_news(keyword, limit=10):
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
# ===== 6️⃣ 計算文章分數（語意 + 關鍵字）=====
def compute_score(text, keywords):
    query_emb = model.encode(st.session_state.keyword)
    sem = semantic_score(query_emb, text)
    key = keyword_score(text, keywords)
    return sem * 0.7 + key * 0.3
# ===== 7️⃣ UI =====
st.title("🔍 智能搜尋器 Pro")
# 輸入欄位 + 筆數
col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])
# 選擇來源
source = st.radio("資料來源", ["PTT", "新聞", "全部"])
# ===== 8️⃣ 搜尋按鈕 =====
if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋 + AI分析中..."):
        data = []
        # 一次抓齊所有來源
        data += fetch_ptt(keyword, limit)
        data += fetch_news(keyword, limit)
        # 排序
        data.sort(key=lambda x: x["score"], reverse=True)
        st.session_state.data = data
        st.session_state.keyword = keyword
        st.session_state.searched = True

# ===== 9️⃣ 顯示結果 =====
if st.session_state.searched:
    # radio 篩選資料
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