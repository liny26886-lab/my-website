import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re

# ===== 基本設定 =====
st.set_page_config(page_title="智能搜尋器 Pro", page_icon="🔍", layout="wide")

# ===== Session 初始化 =====
if "ptt" not in st.session_state:
    st.session_state.ptt = []
if "news" not in st.session_state:
    st.session_state.news = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "keyword" not in st.session_state:
    st.session_state.keyword = ""

# ===== 高亮關鍵字 =====
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

# ===== 計算文章相關度 =====
def compute_relevance(text, keywords):
    return sum(text.lower().count(k.lower()) for k in keywords)

# ===== PTT 搜尋 =====
def fetch_ptt(keyword, board="Gossiping", limit=5, max_pages=5):
    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}

    keywords = re.split(r"\s+", keyword)
    articles = []

    try:
        res = requests.get(f"{PTT_URL}/bbs/{board}/index.html", headers=headers, cookies=cookies, timeout=5)
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
            res = requests.get(f"{PTT_URL}/bbs/{board}/index{page_num}.html",
                               headers=headers, cookies=cookies, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")

            for a in soup.select(".r-ent .title a"):
                title = a.text.strip()
                link = PTT_URL + a["href"]

                score = sum(1 for kw in keywords if kw.lower() in title.lower())
                if score > 0:
                    articles.append({
                        "title": title,
                        "link": link,
                        "score": score
                    })
        except:
            continue

    articles = sorted(articles, key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# ===== 新聞搜尋 =====
def fetch_news(keyword, limit=10):
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []

    try:
        feed = feedparser.parse(RSS_URL)
    except:
        return []

    keywords_list = keyword.split()

    for entry in feed.entries:
        title = BeautifulSoup(entry.title, "html.parser").text
        link = entry.link

        relevance = compute_relevance(title, keywords_list)
        if relevance > 0:
            articles.append({
                "title": title,
                "link": link,
                "relevance": relevance
            })

    articles.sort(key=lambda x: x["relevance"], reverse=True)
    return articles[:limit]

# ===== AI 摘要 =====
def fake_summary(data, keyword):
    if not data:
        return "沒有資料可以分析"
    return f"共找到 {len(data)} 筆資料，主要內容與「{keyword}」相關。"

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")
st.markdown("### 🚀 PTT / 自由時報新聞 一站式搜尋")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋中..."):
        st.session_state.ptt = fetch_ptt(keyword, limit=limit)  # ✅ 修正這裡
        st.session_state.news = fetch_news(keyword, limit)
        st.session_state.keyword = keyword
        st.session_state.searched = True

if st.session_state.searched:
    st.success(f"搜尋關鍵字：{st.session_state.keyword}")
    source = st.radio("資料來源", ["PTT", "新聞"])

    data = st.session_state.ptt if source == "PTT" else st.session_state.news

    st.info(f"共找到 {len(data)} 筆資料")
    st.markdown("### 🧠 AI 摘要")
    st.write(fake_summary(data, st.session_state.keyword))

    for article in data[:5]:
        title = highlight(article["title"], st.session_state.keyword)

        st.markdown(f"""
        <div style="
            background:#1e1e1e;
            padding:15px;
            border-radius:12px;
            margin-bottom:10px;
        ">
            <h4 style="color:white;">{title}</h4>
            <a href="{article['link']}" target="_blank" style="color:#4da6ff;">查看文章 →</a>
        </div>
        """, unsafe_allow_html=True)