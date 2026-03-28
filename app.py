import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re

# ===== 基本設定 =====
st.set_page_config(page_title="智能搜尋器 Pro", page_icon="🔍", layout="wide")

# ===== Session 初始化 =====
for key in ["ptt", "news", "searched", "keyword"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key not in ["searched", "keyword"] else False

# ===== 高亮關鍵字 =====
def highlight(text, keyword):
    if not text:
        return ""
    return re.sub(f"({'|'.join(map(re.escape, keyword.split()))})",
                  r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
                  text,
                  flags=re.IGNORECASE)

# ===== 計算文章相關度 =====
def compute_relevance(text, keywords):
    count = 0
    for k in keywords:
        count += text.lower().count(k.lower())
    return count

# ===== PTT 官方搜尋 =====
def fetch_ptt(keyword, board="Gossiping", limit=5, max_pages=5):
    """
    從最新文章逐頁抓取 PTT 文章，拆解關鍵字計算相關度，
    刪除相關度為 0 的文章，並返回前 limit 筆。
    """
    import requests
    from bs4 import BeautifulSoup
    import re

    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}

    keywords = re.split(r"\s+", keyword)  # 拆解關鍵字
    articles = []

    # 從最新頁開始抓
    try:
        index_res = requests.get(f"{PTT_URL}/bbs/{board}/index.html", headers=headers, cookies=cookies, timeout=5)
        index_soup = BeautifulSoup(index_res.text, "html.parser")
        # 找到最新頁數
        btn = index_soup.select("a.btn.wide")
        max_index = 0
        for b in btn:
            if "上頁" in b.text:
                href = b["href"]
                match = re.search(r"index(\d+).html", href)
                if match:
                    max_index = int(match.group(1)) + 1  # 最新頁
                    break
    except Exception:
        return []

    # 逐頁抓文章
    pages_checked = 0
    for page_num in range(max_index, max_index - max_pages, -1):
        if page_num <= 0:
            break
        try:
            res = requests.get(f"{PTT_URL}/bbs/{board}/index{page_num}.html", headers=headers, cookies=cookies, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")
            entries = soup.select(".r-ent .title a")
            for a in entries:
                title = a.text.strip()
                link = PTT_URL + a["href"]
                # 計算相關度
                score = sum(1 for kw in keywords if kw.lower() in title.lower())
                if score > 0:
                    articles.append({"title": title, "link": link, "score": score})
        except Exception:
            continue
        pages_checked += 1
        if pages_checked >= max_pages:
            break

    # 按相關度排序，取前 limit 筆
    articles = sorted(articles, key=lambda x: x["score"], reverse=True)[:limit]
    return articles

# ===== 自由時報新聞搜尋（RSS） =====
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
            articles.append({"title": title, "link": link, "relevance": relevance})

    # 依相關度排序並取前 limit 筆
    articles.sort(key=lambda x: x["relevance"], reverse=True)
    return articles[:limit]

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
    with st.spinner("搜尋中..."):
        st.session_state.ptt = fetch_ptt_official_search(keyword, limit)
        st.session_state.news = fetch_news(keyword, limit)
        st.session_state.keyword = keyword
        st.session_state.searched = True

if st.session_state.searched:
    st.success(f"搜尋關鍵字：{st.session_state.keyword}")
    source = st.radio("資料來源", ["PTT", "新聞"])

    data = st.session_state.ptt if source == "PTT" else st.session_state.news

    st.info(f"共找到 {len(data)} 筆資料")
    st.markdown("### 🧠 AI 摘要")
    st.write(fake_summary(data))

    # 顯示前5筆
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