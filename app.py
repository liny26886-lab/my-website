import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re

# ===== 基本設定 =====
st.set_page_config(page_title="PTT 智能搜尋器 Pro", page_icon="🔍", layout="wide")

# ===== Session 初始化 =====
st.session_state.setdefault("keyword", "")
st.session_state.setdefault("searched", False)
st.session_state.setdefault("ptt", [])
st.session_state.setdefault("news", [])

# ===== 高亮關鍵字 =====
def highlight(text, keyword):
    if not text:
        return ""
    return re.sub(f"({re.escape(keyword)})",
                  r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
                  text,
                  flags=re.IGNORECASE)

# ===== PTT 官方搜尋 =====
def fetch_ptt_official_search(keyword, board="Gossiping", limit=10):
    PTT_URL = "https://www.ptt.cc"
    SEARCH_URL = f"{PTT_URL}/bbs/{board}/SearchResult.jsp"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9"
    }
    cookies = {"over18": "1"}
    articles = []

    try:
        payload = {"keyword": keyword, "searchtype": "title", "start": "0"}
        res = requests.post(SEARCH_URL, data=payload, headers=headers, cookies=cookies, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        entries = soup.select(".r-ent .title a")
        for a in entries[:limit]:
            title = a.text.strip()
            link = PTT_URL + a["href"]
            articles.append({"title": title, "link": link})
    except Exception:
        pass

    return articles

# ===== 自由時報新聞搜尋 =====
def fetch_news(keyword, limit=10):
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception:
        return []

    for entry in feed.entries:
        title = BeautifulSoup(entry.title, "html.parser").text.strip()
        link = entry.link
        if keyword.lower() in title.lower():
            articles.append({"title": title, "link": link})
        if len(articles) >= limit:
            break

    return articles

# ===== AI 摘要（簡化版） =====
def fake_summary(data):
    if not data:
        return "沒有資料可以分析"
    return f"共找到 {len(data)} 筆資料，主要內容與「{st.session_state.keyword}」相關，建議優先查看前幾篇熱門文章。"

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")
st.markdown("### 🚀 PTT / 自由時報新聞 一站式搜尋")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋中…"):
        st.session_state.ptt = fetch_ptt_official_search(keyword, limit)
        st.session_state.news = fetch_news(keyword, limit)
        st.session_state.keyword = keyword
        st.session_state.searched = True

if st.session_state.searched:
    st.success(f"搜尋關鍵字：{st.session_state.keyword}")
    source = st.radio("資料來源", ["PTT", "新聞"])

    data = st.session_state.ptt if source == "PTT" else st.session_state.news

    if not data:
        st.info("目前沒有資料可以顯示")
    else:
        st.info(f"共找到 {len(data)} 筆資料")
        st.markdown("### 🧠 AI 摘要")
        st.write(fake_summary(data))

        # 分頁顯示
        page_size = 5
        total_pages = (len(data)-1)//page_size + 1
        page = st.number_input("頁數", min_value=1, max_value=total_pages, step=1)
        start = (page - 1) * page_size
        end = start + page_size

        for article in data[start:end]:
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
else:
    st.warning("請先輸入關鍵字並搜尋")