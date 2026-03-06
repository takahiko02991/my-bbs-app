import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib

# 1. 接続設定
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="休サイト", page_icon="💬", layout="centered")

# 匿名ID生成
def get_trip_id():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return hashlib.sha256(date_str.encode()).hexdigest()[:8]

# --- ヘッダー ---
st.title("休サイト ※なかよくしろよ")
st.caption(f"現在のID: `{get_trip_id()}` | [URLコピー](https://my-bbs-app.streamlit.app/)")

# --- ① スレッド情報の取得 ---
# 全投稿から thread_title を取得して、各スレの「最新投稿日時」と「レス数」を計算
res_all = supabase.table("bbs_posts").select("thread_title, created_at").execute()
data = res_all.data

thread_info = {}
for item in data:
    title = item['thread_title'] if item['thread_title'] else "雑談"
    if title not in thread_info:
        thread_info[title] = {"count": 0, "latest": item['created_at']}
    thread_info[title]["count"] += 1
    if item['created_at'] > thread_info[title]["latest"]:
        thread_info[title]["latest"] = item['created_at']

# スレッドを「最新の書き込み順」で並び替え
sorted_threads = sorted(thread_info.items(), key=lambda x: x[1]['latest'], reverse=True)

# --- ② 画面切り替え（スレッド一覧 or スレッド内） ---
# セッション状態（ブラウザを閉じても保持される記憶）を使って、今どのスレを見てるか管理
if "current_thread" not in st.session_state:
    st.session_state.current_thread = None

# --- スレッド一覧画面 ---
if st.session_state.current_thread is None:
    st.subheader("🧵 スレッド一覧")
    
    # 新規スレッド作成
    with st.expander("➕ 新しいスレッドを立てる"):
        with st.form("new_thread_form"):
            new_t = st.text_input("スレッド名")
            name = st.text_input("名前", placeholder="風吹けば恋さん")
            msg = st.text_area("最初の書き込み")
            if st.form_submit_button("スレッド作成"):
                if new_t and msg:
                    supabase.table("bbs_posts").insert({
                        "thread_title": new_t,
                        "name": name if name else "風吹けば恋さん",
                        "content": msg,
                        "user_id": get_trip_id()
                    }).execute()
                    st.session_state.current_thread = new_t
                    st.rerun()

    # 一覧表示
    for title, info in sorted_threads:
        if st.button(f"{title} ({info['count']})", use_container_width=True):
            st.session_state.current_thread = title
            st.rerun()

# --- スレッド内画面 ---
else:
    if st.button("⬅ スレッド一覧に戻る"):
        st.session_state.current_thread = None
        st.rerun()

    st.header(f"🔥 {st.session_state.current_thread}")

    # 書き込みフォーム
    with st.expander("💬 このスレに書き込む"):
        with st.form("post_in_thread"):
            name = st.text_input("名前", placeholder="風吹けば恋さん")
            msg = st.text_area("本文")
            if st.form_submit_button("書き込む"):
                if msg:
                    supabase.table("bbs_posts").insert({
                        "thread_title": st.session_state.current_thread,
                        "name": name if name else "風吹けば恋さん",
                        "content": msg,
                        "user_id": get_trip_id()
                    }).execute()
                    st.rerun()

    # レス表示（2chっぽく古い順から表示）
    res = supabase.table("bbs_posts").select("*").eq("thread_title", st.session_state.current_thread).order("created_at", desc=False).execute()
    
    for i, post in enumerate(res.data):
        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
        time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
        
        # 2chのデザイン（1：名前：日付 ID：）
        st.markdown(f"**{i+1}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{post['user_id']}", unsafe_allow_html=True)
        st.write(post['content'])
        st.divider()
            st.markdown(f"**{post_num}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{post['user_id']}", unsafe_allow_html=True)
            st.write(post['content'])


            
