import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# ===== 基本設定 =====
st.set_page_config(page_title="PTT 智能搜尋器 Pro", page_icon="🔍", layout="wide")
PTT_URL = "https://www.ptt.cc"

# ===== session 初始化 =====
for key in ["ptt", "news", "law", "searched", "keyword"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key != "searched" and key != "keyword" else False

# ===== 抓資料 =====
def fetch_ptt_articles(keyword, limit):
    url = f"{PTT_URL}/bbs/Gossiping/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = {'over18': '1'}

    articles, page_count = [], 0

    while len(articles) < limit and page_count < 10:
        res = requests.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(res.text, "html.parser")

        for entry in soup.select(".r-ent"):
            tag = entry.select_one(".title a")
            if not tag:
                continue
            title = tag.text
            if keyword.lower() in title.lower():
                articles.append({
                    "title": title,
                    "link": PTT_URL + tag["href"]
                })
        # 上頁
        btn = soup.select(".btn-group-paging a")[1]
        url = PTT_URL + btn["href"]
        page_count += 1

    return articles[:limit]


def fetch_news(keyword, limit):
    url = "https://news.ltn.com.tw/list/breakingnews"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    articles = []
    for a in soup.select(".whitecon h3 a"):
        if keyword.lower() in a.text.lower():
            articles.append({"title": a.text, "link": a["href"]})

    return articles[:limit]


def fetch_laws(keyword, limit):
    url = f"https://law.moj.gov.tw/LawClass/LawSearch?query={keyword}"
    res = requests.get(url, verify=False)
    soup = BeautifulSoup(res.text, "html.parser")

    articles = []
    for a in soup.select(".search_result_title a"):
        articles.append({
            "title": a.text,
            "link": "https://law.moj.gov.tw" + a["href"]
        })

    return articles[:limit]

# ===== 高亮 =====
def highlight(text, keyword):
    return re.sub(f"({keyword})",
                  r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
                  text,
                  flags=re.IGNORECASE)

# ===== AI 摘要（簡化版）=====
def fake_summary(data):
    if not data:
        return "沒有資料可以分析"
    return f"共找到 {len(data)} 筆資料，主要內容與「{st.session_state.keyword}」相關，建議優先查看前幾篇熱門文章。"

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")
st.markdown("### 🚀 PTT / 新聞 / 法規 一站式搜尋")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

# ===== 搜尋 =====
if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("搜尋中..."):
        st.session_state.ptt = fetch_ptt_articles(keyword, limit)
        st.session_state.news = fetch_news(keyword, limit)
        st.session_state.law = fetch_laws(keyword, limit)
        st.session_state.keyword = keyword
        st.session_state.searched = True

# ===== 顯示區 =====
if st.session_state.searched:

    st.success(f"搜尋關鍵字：{st.session_state.keyword}")

    source = st.radio("資料來源", ["PTT", "新聞", "法規"])

    if source == "PTT":
        data = st.session_state.ptt
    elif source == "新聞":
        data = st.session_state.news
    else:
        data = st.session_state.law

    # ===== 統計 =====
    st.info(f"共找到 {len(data)} 筆資料")

    # ===== AI摘要 =====
    st.markdown("### 🧠 AI 摘要")
    st.write(fake_summary(data))

    # ===== 分頁 =====
    page_size = 5
    page = st.number_input("頁數", min_value=1, max_value=max(1, len(data)//page_size + 1), step=1)

    start = (page - 1) * page_size
    end = start + page_size

    # ===== 卡片顯示 =====
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
            <a href="{article['link']}" target="_blank">查看文章 →</a>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning("請先輸入關鍵字並搜尋")