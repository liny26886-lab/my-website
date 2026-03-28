import streamlit as st
import requests
from bs4 import BeautifulSoup

# ===== Streamlit 頁面設定 =====
st.set_page_config(page_title="PTT 智能搜尋器", page_icon="🔍", layout="wide")
PTT_URL = "https://www.ptt.cc"

# ===== 函式區 =====
def fetch_ptt_articles(keyword="ai", limit=10):
    url = f"{PTT_URL}/bbs/Gossiping/index.html"
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

        # 下一頁按鈕
        btn_prev = soup.select_one(".btn-group-paging a:contains('上頁')")
        if btn_prev and "href" in btn_prev.attrs:
            url = PTT_URL + btn_prev["href"]
        else:
            url = None
        page_count += 1

    return articles

def fetch_news(keyword, limit=10):
    url = "https://news.ltn.com.tw/list/breakingnews"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    articles = []
    for entry in soup.select(".whitecon h3 a")[:limit]:
        if keyword.lower() in entry.text.lower():
            articles.append({"title": entry.text.strip(), "link": entry["href"]})
    return articles

def fetch_laws(keyword, limit=10):
    import requests
    from bs4 import BeautifulSoup

    url = f"https://law.moj.gov.tw/LawClass/LawSearch?query={keyword}"
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []

    try:
        res = requests.get(url, headers=headers, timeout=5, verify=False)
    except Exception as e:
        print(f"Error fetching law site: {e}")
        return articles

    soup = BeautifulSoup(res.text, "html.parser")
    for entry in soup.select(".search_result_title a")[:limit]:
        articles.append({"title": entry.text.strip(), "link": "https://law.moj.gov.tw" + entry["href"]})
        if len(articles) >= limit:
            break

    return articles[:limit]
def highlight(text, keyword):
    """高亮關鍵字"""
    return text.replace(keyword, f"<span style='color:#ffea00;font-weight:bold'>{keyword}</span>")

# ===== 主畫面 =====
st.title("🔍 PTT 智能搜尋器（作品集版）")
st.markdown("### 🚀 快速搜尋 PTT / 新聞 / 法規")

col1, col2 = st.columns([3,1])
with col1:
    keyword = st.text_input("輸入關鍵字", placeholder="例如：AI、股票、遊戲")
with col2:
    limit = st.selectbox("筆數", [5, 10, 20])

if st.button("開始搜尋 🔍") and keyword:
    with st.spinner("抓取資料中..."):
        ptt_results = fetch_ptt_articles(keyword=keyword, limit=limit)
        news_results = fetch_news(keyword=keyword, limit=limit)
        law_results = fetch_laws(keyword=keyword, limit=limit)

    st.success("✅ 搜尋完成！")

    # 選擇資料來源
    source = st.radio("選擇資料來源", ["PTT", "新聞", "法規"])
    
    if source == "PTT":
        data = ptt_results
    elif source == "新聞":
        data = news_results
    else:
        data = law_results

    if not data:
        st.warning("沒有找到相關文章。")
    else:
        for article in data:
            display_title = highlight(article['title'], keyword)
            st.markdown(f"""
            <div style="
                background-color:#1e1e1e;
                padding:15px;
                border-radius:12px;
                margin-bottom:10px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            ">
                <h4 style="color:white;">{display_title}</h4>
                <a href="{article['link']}" target="_blank" style="color:#4da6ff;">
                    點我查看文章 →
                </a>
            </div>
            """, unsafe_allow_html=True)