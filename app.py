import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time

# ===== 基本設定 =====
st.set_page_config(page_title="PTT 智能搜尋器 Pro", page_icon="🔍", layout="wide")
PTT_URL = "https://www.ptt.cc"

# ===== session 初始化（修正型別🔥）=====
if "ptt" not in st.session_state:
    st.session_state.ptt = []
if "news" not in st.session_state:
    st.session_state.news = []
if "law" not in st.session_state:
    st.session_state.law = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "keyword" not in st.session_state:
    st.session_state.keyword = ""

# ===== 抓資料（強化穩定） =====
def fetch_ptt_articles(keyword, limit):
    url = f"{PTT_URL}/bbs/Gossiping/index.html"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "zh-TW,zh;q=0.9"
    }
    cookies = {'over18': '1'}

    articles = []
    page_count = 0

    try:
        while len(articles) < limit and page_count < 5:
            res = requests.get(url, headers=headers, cookies=cookies, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            for entry in soup.select(".r-ent"):
                tag = entry.select_one(".title a")
                if not tag:
                    continue

                title = tag.text.strip()
                if keyword.lower() in title.lower():
                    articles.append({
                        "title": title,
                        "link": PTT_URL + tag["href"]
                    })

            btns = soup.select(".btn-group-paging a")
            if len(btns) >= 2:
                url = PTT_URL + btns[1]["href"]
            else:
                break

            page_count += 1
            time.sleep(1)  # 防封

    except Exception as e:
        st.warning("⚠️ PTT 抓取失敗（可能被擋）")

    return articles[:limit]


def fetch_news(keyword, limit):
    try:
        url = "https://news.ltn.com.tw/list/breakingnews"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        articles = []
        for a in soup.select(".whitecon h3 a"):
            if keyword.lower() in a.text.lower():
                articles.append({"title": a.text, "link": a["href"]})

        return articles[:limit]

    except:
        st.warning("⚠️ 新聞抓取失敗")
        return []


def fetch_laws(keyword, limit):
    try:
        url = f"https://law.moj.gov.tw/LawClass/LawSearch?query={keyword}"
        res = requests.get(url, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, "html.parser")

        articles = []
        for a in soup.select(".search_result_title a"):
            articles.append({
                "title": a.text,
                "link": "https://law.moj.gov.tw" + a["href"]
            })

        return articles[:limit]

    except:
        st.warning("⚠️ 法規抓取失敗")
        return []

# ===== 高亮 =====
def highlight(text, keyword):
    return re.sub(f"({keyword})",
                  r"<span style='color:#ffea00;font-weight:bold'>\1</span>",
                  text,
                  flags=re.IGNORECASE)

# ===== UI =====
st.title("🔍 智能搜尋器 Pro")
st.markdown("### 🚀 PTT / 新聞 / 法規 一站式搜尋")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", value=st.session_state.keyword)
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

# ===== 搜尋（只記錄 keyword）=====
if st.button("開始搜尋 🔍") and keyword:
    st.session_state.keyword = keyword
    st.session_state.searched = True
    # 清空舊資料（重要🔥）
    st.session_state.ptt = []
    st.session_state.news = []
    st.session_state.law = []

# ===== 顯示區 =====
if st.session_state.searched:

    st.success(f"搜尋關鍵字：{st.session_state.keyword}")

    source = st.radio("資料來源", ["PTT", "新聞", "法規"])

    # ===== 懶載入（重點🔥）=====
    with st.spinner("載入資料中..."):
        if source == "PTT" and not st.session_state.ptt:
            st.session_state.ptt = fetch_ptt_articles(st.session_state.keyword, limit)

        elif source == "新聞" and not st.session_state.news:
            st.session_state.news = fetch_news(st.session_state.keyword, limit)

        elif source == "法規" and not st.session_state.law:
            st.session_state.law = fetch_laws(st.session_state.keyword, limit)

    # ===== 選資料 =====
    if source == "PTT":
        data = st.session_state.ptt
    elif source == "新聞":
        data = st.session_state.news
    else:
        data = st.session_state.law

    # ===== icon =====
    icon = {"PTT": "💬", "新聞": "📰", "法規": "⚖️"}
    st.markdown(f"### {icon[source]} {source}")

    # ===== 統計 =====
    st.info(f"共找到 {len(data)} 筆資料")

    # ===== 空資料處理（產品級🔥）=====
    if not data:
        st.warning(f"{source} 沒有資料或暫時無法取得")
    else:
        # ===== 分頁 =====
        page_size = 5
        max_page = max(1, len(data)//page_size + 1)
        page = st.number_input("頁數", min_value=1, max_value=max_page, step=1)

        start = (page - 1) * page_size
        end = start + page_size

        # ===== 卡片 =====
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