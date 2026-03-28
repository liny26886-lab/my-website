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

# ===== 關鍵字處理 =====
def get_keywords(keyword):
    return [k for k in re.split(r"\s+", keyword) if k]

# ===== 高亮 =====
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

# ===== 🔥 核心評分系統 =====
def compute_score(text, keywords):
    text_lower = text.lower()
    score = 0

    for kw in keywords:
        kw_lower = kw.lower()

        # 完整匹配
        if kw_lower in text_lower:
            score += 5

        # 子字串
        for i in range(len(kw_lower)):
            for j in range(i+2, len(kw_lower)+1):
                sub = kw_lower[i:j]
                if sub in text_lower:
                    score += 2

        # 單字匹配
        for char in kw_lower:
            if char in text_lower:
                score += 1

    return score

# ===== PTT =====
def fetch_ptt(keyword, board="Gossiping", limit=10, max_pages=5):
    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}

    keywords = get_keywords(keyword)
    articles = []

    try:
        res = requests.get(f"{PTT_URL}/bbs/{board}/index.html", headers=headers, cookies=cookies)
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
                               headers=headers, cookies=cookies)
            soup = BeautifulSoup(res.text, "html.parser")

            for a in soup.select(".r-ent .title a"):
                title = a.text.strip()
                link = PTT_URL + a["href"]

                score = compute_score(title, keywords)

                if score >= 2:   # 🔥 過濾低品質
                    articles.append({
                        "title": title,
                        "link": link,
                        "score": score
                    })
        except:
            continue

    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# ===== 新聞 =====
def fetch_news(keyword, limit=10):
    RSS_URL = "https://news.ltn.com.tw/rss/all.xml"
    articles = []

    try:
        feed = feedparser.parse(RSS_URL)
    except:
        return []

    keywords = get_keywords(keyword)

    for entry in feed.entries:
        title = BeautifulSoup(entry.title, "html.parser").text
        link = entry.link

        score = compute_score(title, keywords)

        if score >= 2:
            articles.append({
                "title": title,
                "link": link,
                "score": score
            })

    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋中..."):
        st.session_state.ptt = fetch_ptt(keyword, limit=limit)
        st.session_state.news = fetch_news(keyword, limit)
        st.session_state.keyword = keyword
        st.session_state.searched = True

if st.session_state.searched:
    source = st.radio("資料來源", ["PTT", "新聞"])
    data = st.session_state.ptt if source == "PTT" else st.session_state.news

    st.write(f"共 {len(data)} 筆結果")

    for article in data:
        title = highlight(article["title"], st.session_state.keyword)

        st.markdown(f"""
        <div style="background:#1e1e1e;padding:15px;border-radius:10px;margin-bottom:10px;">
            <h4 style="color:white;">{title}</h4>
            <p style="color:gray;">相關度：{article['score']}</p>
            <a href="{article['link']}" target="_blank">查看文章</a>
        </div>
        """, unsafe_allow_html=True)