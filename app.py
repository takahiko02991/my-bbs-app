import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib
import qrcode
from io import BytesIO
import re
import random
import string
from streamlit_autorefresh import st_autorefresh

# --- 1. ページ設定（一番最初に1回だけ！） ---
st.set_page_config(
    page_title="休サイト - 休憩の匿名掲示板", 
    page_icon="💬", 
    layout="centered"
)

# 5秒ごとに自動更新
st_autorefresh(interval=5000, key="bbs_refresh")

# Google確認用タグ
st.markdown('<meta name="google-site-verification" content="9z3A-fzdRLWmFx2ZNkg47ac0I99VffSQ35i9XERd7v4" />', unsafe_allow_html=True)

# --- 2. 接続設定とセッション初期化 ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(url, key)

if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "current_thread" not in st.session_state:
    st.session_state.current_thread = None

# --- 3. 便利関数 ---
def get_trip_id():
    date_str = datetime.now().strftime("%Y-%m-%d")
    if "user_secret_key" not in st.session_state:
        st.session_state.user_secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    combined = date_str + st.session_state.user_secret_key
    return hashlib.sha256(combined.encode()).hexdigest()[:8]

def show_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf, caption="スマホで読み取って参加！", width=150)

# --- 4. サイドバー（設定・ログイン） ---
with st.sidebar:
    st.title("🛠️ 設定")
    if not st.session_state.admin_mode:
        input_pass = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン"):
            if input_pass == ADMIN_PASSWORD:
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        st.success("管理者モード実行中")
        if st.button("ログアウト"):
            st.session_state.admin_mode = False
            st.rerun()
    
    st.divider()
    app_url = "https://my-bbs-app-6heicw938faphfqgz4ayw5.streamlit.app"
    show_qr(app_url)

# --- 5. メイン画面の分岐 ---

# 【A】管理者モードの時
if st.session_state.admin_mode:
    st.header("⚙️ 投稿管理（削除モード）")
    res = supabase.table("bbs_posts").select("*").order("created_at", desc=True).execute()
    posts = res.data
    if not posts:
        st.info("投稿はまだありません。")
    else:
        for post in posts:
            with st.container(border=True):
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.write(f"**{post['thread_title']}** | **{post['name']}** - {post['created_at']}")
                    st.write(post['content'])
                with col2:
                    if st.button("削除", key=f"del_{post['id']}"):
                        supabase.table("bbs_posts").delete().eq("id", post['id']).execute()
                        st.success("削除しました")
                        st.rerun()

# 【B】一般ユーザーモードの時
else:
    st.title("休サイト なかよくしてね(^ O ^)ﾉｼ)")
    st.caption(f"現在のID: `{get_trip_id()}`")

    # スレッド一覧をDBから集計して取得
    res_all = supabase.table("bbs_posts").select("thread_title, created_at").execute()
    thread_info = {}
    for item in res_all.data:
        title = item['thread_title'] if item['thread_title'] else "雑談"
        if title not in thread_info:
            thread_info[title] = {"count": 0, "latest": item['created_at']}
        thread_info[title]["count"] += 1
        if item['created_at'] > thread_info[title]["latest"]:
            thread_info[title]["latest"] = item['created_at']
    sorted_threads = sorted(thread_info.items(), key=lambda x: x[1]['latest'], reverse=True)

    # --- B-1. スレッド一覧表示中 ---
    if st.session_state.current_thread is None:
        st.write("休サイトは、誰でも気軽に書き込める完全匿名の掲示板アプリです。")
        
        with st.expander("➕ 新しいスレッドを立てる"):
            with st.form("new_thread_form", clear_on_submit=True):
                new_t = st.text_input("スレッド名", max_chars=50)
                name = st.text_input("名前", placeholder="風吹けば恋さん", max_chars=20)
                msg = st.text_area("最初の書き込み", max_chars=1000)
                if st.form_submit_button("スレッド作成"):
                    if new_t.strip() and msg.strip():
                        supabase.table("bbs_posts").insert({
                            "thread_title": new_t.strip(),
                            "name": name.strip() if name.strip() else "風吹けば恋さん",
                            "content": msg.strip(),
                            "user_id": get_trip_id()
                        }).execute()
                        st.session_state.current_thread = new_t.strip()
                        st.rerun()
                    else:
                        st.error("スレッド名と最初の書き込みを入力してください")

        st.subheader("🧵 スレッド一覧")
        for title, info in sorted_threads:
            if st.button(f"{title} ({info['count']})", use_container_width=True, key=f"list_{title}"):
                st.session_state.current_thread = title
                st.rerun()

    # --- B-2. スレッド詳細表示中 ---
    else:
        if st.button("⬅ スレッド一覧に戻る"):
            st.session_state.current_thread = None
            st.rerun()

        st.header(f"🔥 {st.session_state.current_thread}")

        # 書き込みフォーム（スレ内のみ表示）
        with st.expander("💬 このスレに書き込む"):
            with st.form("post_in_thread", clear_on_submit=True):
                input_name = st.text_input("名前", placeholder="風吹けば恋さん", key="input_name_key")
                msg = st.text_area("本文", key="input_msg_key")
                if st.form_submit_button("書き込む"):
                    if msg.strip():
                        supabase.table("bbs_posts").insert({
                            "thread_title": st.session_state.current_thread,
                            "name": input_name if input_name else "風吹けば恋さん",
                            "content": msg.strip(),
                            "user_id": get_trip_id()
                        }).execute()
                        st.toast("書き込み完了！", icon="✅")
                        st.rerun()
                    else:
                        st.error("本文を入力してください")

        # レス表示
        res = supabase.table("bbs_posts").select("*").eq("thread_title", st.session_state.current_thread).order("created_at", desc=False).execute()
        id_counts = {}
        for post in res.data:
            uid = post['user_id']
            id_counts[uid] = id_counts.get(uid, 0) + 1

        for i, post in enumerate(res.data):
            dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
            time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
            uid = post['user_id']
            
            # メンション変換
            def link_repl(match):
                num = match.group(1)
                return f'<span style="color: #1e90ff; font-weight: bold;">>>{num}</span>'
            converted_content = re.sub(r'>>(\d+)', link_repl, post['content'])

            with st.container(border=True):
                st.markdown(f"**{i+1}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{uid} **({id_counts[uid]})**", unsafe_allow_html=True)
                st.markdown(converted_content, unsafe_allow_html=True)


