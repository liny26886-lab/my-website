import streamlit as st
import requests
from bs4 import BeautifulSoup
from functools import lru_cache

# ===== 基本設定 =====
st.set_page_config(page_title="PTT 搜尋器", page_icon="🔍", layout="wide")
PTT_URL = "https://www.ptt.cc"

# ===== 爬蟲 + Cache =====
@st.cache_data(show_spinner=False)
def fetch_ptt_articles(board="Gossiping", keyword="ai", limit=10):
    url = f"{PTT_URL}/bbs/{board}/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = {'over18': '1'}

    articles = []
    page_count = 0
    max_pages = 15

    while len(articles) < limit and url and page_count < max_pages:
        try:
            res = requests.get(url, headers=headers, cookies=cookies, timeout=5)
        except:
            break

        soup = BeautifulSoup(res.text, "html.parser")
        entries = soup.select(".r-ent")

        for entry in entries:
            title_tag = entry.select_one(".title a")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link = PTT_URL + title_tag["href"]

            if keyword.lower() in title.lower():
                articles.append({"title": title, "link": link})

            if len(articles) >= limit:
                break

        btn = soup.select_one(".btn-group-paging a:nth-child(2)")
        url = PTT_URL + btn["href"] if btn else None
        page_count += 1

    return articles

# ===== UI =====
def highlight(text, keyword):
    return text.replace(keyword, f"**{keyword}**")

def show_card(title, link, keyword):
    st.markdown(f"""
    <div style="
        background-color:#1e1e1e;
        padding:15px;
        border-radius:12px;
        margin-bottom:10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    ">
        <h4 style="color:white;">{highlight(title, keyword)}</h4>
        <a href="{link}" target="_blank" style="color:#4da6ff;">
            點我查看文章 →
        </a>
    </div>
    """, unsafe_allow_html=True)

# ===== 主畫面 =====
st.title("🔍 PTT 智能搜尋器（作品集版）")
st.markdown("### 🚀 快速搜尋 PTT 熱門討論")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", placeholder="例如：AI、股票、遊戲")
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍"):
    if not keyword:
        st.warning("請輸入關鍵字！")
    else:
        with st.spinner("🔎 搜尋中，請稍候..."):
            results = fetch_ptt_articles(keyword=keyword, limit=limit)

        st.divider()

        if not results:
            st.error("❌ 找不到相關文章（可能被 PTT 擋了）")
        else:
            st.success(f"✅ 找到 {len(results)} 筆結果")
            for article in results:
                show_card(article["title"], article["link"], keyword)