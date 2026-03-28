import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re

# ===== 基本設定 =====
st.set_page_config(page_title="PTT 智能搜尋器 Pro", page_icon="🔍", layout="wide")

# ===== Session 初始化 =====
for key in ["ptt", "news", "searched", "keyword"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key not in ["searched", "keyword"] else False

# ===== 高亮關鍵字 =====
def highlight(text, keywords):
    if not text:
        return ""
    # 逐個關鍵字高亮
    for kw in keywords:
        text = re.sub(f"({re.escape(kw)})",
                      r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
                      text,
                      flags=re.IGNORECASE)
    return text

# ===== PTT 官方搜尋 =====
def fetch_ptt_official_search(keyword, board="Gossiping", limit=10):
    PTT_URL = "https://www.ptt.cc"
    SEARCH_URL = f"{PTT_URL}/bbs/{board}/SearchResult.jsp"
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = {"over18": "1"}
    articles = []

    try:
        payload = {"keyword": keyword, "searchtype": "title", "start": "0"}
        res = requests.post(SEARCH_URL, data=payload, headers=headers, cookies=cookies, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        entries = soup.select(".r-ent .title a")
        for a in entries:
            title = a.text.strip()
            link = PTT_URL + a["href"]
            articles.append({"title": title, "link": link})
    except Exception as e:
        st.warning(f"PTT 搜尋遇到問題: {e}")

    return articles

# ===== 自由時報新聞搜尋（RSS） =====
def fetch_news(keyword, limit=10):
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception:
        return []

    for entry in feed.entries:
        title = BeautifulSoup(entry.title, "html.parser").text
        link = entry.link
        articles.append({"title": title, "link": link})
    return articles

# ===== 計算匹配度 =====
def match_score(title, keywords):
    score = 0
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() in title_lower:
            score += 1
    return score

# ===== AI 摘要（簡化版） =====
def fake_summary(data):
    if not data:
        return "沒有資料可以分析"
    return f"共找到 {len(data)} 筆資料，主要內容與「{st.session_state.keyword}」相關，建議優先查看前幾篇熱門文章。"

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")
st.markdown("### 🚀 PTT / 自由時報新聞 一站式搜尋（關鍵字拆解 + 排序）")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋中..."):
        keywords = keyword.split()  # 拆解關鍵字
        st.session_state.ptt = fetch_ptt_official_search(keyword, limit=50)  # 先抓多一點
        st.session_state.news = fetch_news(keyword, limit=50)
        st.session_state.keyword = keyword
        st.session_state.searched = True
        st.session_state.keywords_list = keywords

if st.session_state.searched:
    st.success(f"搜尋關鍵字：{st.session_state.keyword}")
    source = st.radio("資料來源", ["PTT", "新聞"])

    data = st.session_state.ptt if source == "PTT" else st.session_state.news

    # 計算匹配度
    for article in data:
        article["score"] = match_score(article["title"], st.session_state.keywords_list)

    # 按匹配度排序
    data_sorted = sorted(data, key=lambda x: x["score"], reverse=True)

    # 取前 5 筆
    top5 = data_sorted[:5]

    st.info(f"共找到 {len(data)} 筆資料，前 5 筆最相關")

    st.markdown("### 🧠 AI 摘要")
    st.write(fake_summary(top5))

    for article in top5:
        title = highlight(article["title"], st.session_state.keywords_list)
        st.markdown(f"""
        <div style="
            background:#1e1e1e;
            padding:15px;
            border-radius:12px;
            margin-bottom:10px;
        ">
            <h4 style="color:white;">{title}</h4>
            <a href="{article['link']}" target="_blank" style="color:#4da6ff;">查看文章 →</a>
            <p style="color:#ffea00;">匹配關鍵字數量：{article['score']}</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.warning("請先輸入關鍵字並搜尋")