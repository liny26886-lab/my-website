import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import re

# =========================
# 1️⃣ 設定
# =========================
st.set_page_config(page_title="智能搜尋器 Pro（穩定版）", layout="wide")
progress_text = st.empty()
progress_bar = st.progress(0)
# =========================
# 2️⃣ Session
# =========================
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
    return [k.lower() for k in re.split(r"\s+", keyword) if k]
def keyword_score(text, keywords):
    text = text.lower()
    return sum(2 for kw in keywords if kw in text)
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
# 4️⃣ PTT 搜尋（穩定版）
# =========================
def fetch_ptt_multi(keyword, limit=20, max_pages=10):

    boards = ["Gossiping", "Tech_Job", "Stock", "Soft_Job", "NBA"]

    PTT_URL = "https://www.ptt.cc"
    cookies = {"over18": "1"}
    headers = {"User-Agent": "Mozilla/5.0"}

    keywords = get_keywords(keyword)
    articles = []

    for board in boards:

        try:
            # 取得最新頁碼
            res = requests.get(
                f"{PTT_URL}/bbs/{board}/index.html",
                headers=headers,
                cookies=cookies,
                timeout=5
            )
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
            continue

        # 抓多頁
        for page in range(max_index, max_index - max_pages, -1):

            try:
                res = requests.get(
                    f"{PTT_URL}/bbs/{board}/index{page}.html",
                    headers=headers,
                    cookies=cookies,
                    timeout=5
                )
                soup = BeautifulSoup(res.text, "html.parser")
                for a in soup.select(".r-ent .title a"):
                    title = a.text.strip()
                    link = PTT_URL + a["href"]
                    score = keyword_score(title, keywords)
                    if score > 1:
                        articles.append({
                            "title": f"[{board}] {title}",
                            "link": link,
                            "score": score,
                            "source": "PTT"
                        })

            except:
                continue

    return articles

# =========================
# 5️⃣ News 搜尋（穩定版）
# =========================
def fetch_google_news(keyword, limit=20):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(url)
    articles = []
    for e in feed.entries[:limit]:
        title = BeautifulSoup(e.title, "html.parser").text
        link = e.link
        articles.append({
            "title": title,
            "link": link,
            "score": 2,  # 基本分
            "source": "Google"
        })
    return articles
def fetch_multi_news(keyword, limit=20):

    rss_list = [
        "https://news.ltn.com.tw/rss/all.xml",
        "https://udn.com/rssfeed/news/2/6638?ch=news",
        "https://www.cna.com.tw/rss/aall.aspx"
    ]
    keywords = get_keywords(keyword)
    articles = []
    for rss in rss_list:
        feed = feedparser.parse(rss)
        for e in feed.entries:
            if hasattr(e, "title") and hasattr(e, "link"):
                title = e.title
                link = e.link
                score = keyword_score(title, keywords)
                if score > 1:
                    articles.append({
                        "title": title,
                        "link": link,
                        "score": score,
                        "source": "新聞"
                    })
    return articles
# =========================
# 6️⃣ UI
# =========================
st.title("🔍 智能搜尋器 Pro（超穩關鍵字版）")
col1, col2 = st.columns([3, 1])
with col1:
    keyword_input = st.text_input("輸入關鍵字")
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])
source = st.radio("資料來源", ["PTT", "新聞", "全部"])

# =========================
# 7️⃣ 搜尋邏輯
# =========================
if st.button("開始搜尋 🔍"):
    st.session_state.keyword = keyword_input
    progress_text.text("開始搜尋...")
    progress_bar.progress(0)
    data = []
    if source in ["PTT", "全部"]:
        data += fetch_ptt_multi(keyword_input, limit)
    progress_bar.progress(20)
    if source in ["新聞", "全部"]:
        data += fetch_multi_news(keyword_input, limit)
        data += fetch_google_news(keyword_input, limit)
    progress_bar.progress(80)
    data.sort(key=lambda x: x["score"], reverse=True)
    data[:limit]
    st.session_state.data = data
    st.session_state.searched = True
    progress_text.text("完成")
    progress_bar.progress(100)
# =========================
# 8️⃣ 顯示結果
# =========================
if st.session_state.searched:
    st.write(f"共 {len(st.session_state.data)} 筆結果")
    for a in st.session_state.data:
        title = highlight(a["title"], st.session_state.keyword)
        st.markdown(f"""
        <div style="background:#1e1e1e;padding:15px;border-radius:10px;margin-bottom:10px;">
            <h4 style="color:white;">{title}</h4>
            <p style="color:gray;">相關度：{a['score']}</p>
            <a href="{a['link']}" target="_blank">查看</a>
        </div>
        """, unsafe_allow_html=True)