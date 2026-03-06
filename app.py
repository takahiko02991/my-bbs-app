import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib
import qrcode
from io import BytesIO

# 1. 接続設定
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="休サイト", page_icon="💬", layout="centered")

# 匿名ID生成
# 修正版：もっとバラバラになるID生成
def get_trip_id():
    # 1. 今日の日付（これは日付でリセットするために残す）
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 2. セッションID（アクセスした人ごとに発行されるランダムなID）
    # これを使えば、たとえ同じiPhone同士でも、アクセスした瞬間に別々のIDが割り振られます
    if "user_secret_key" not in st.session_state:
        # 初めてアクセスした時にランダムな文字列を作る
        import random
        import string
        st.session_state.user_secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # 日付と、その人専用の秘密キーを合体！
    combined = date_str + st.session_state.user_secret_key
    return hashlib.sha256(combined.encode()).hexdigest()[:8]

# --- QRコードを生成する関数 ---
def show_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 画像をメモリに保存してStreamlitで表示できる形式にする
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf, caption="スマホで読み取って参加！", width=150)
# --- ヘッダー ---
st.title("休サイト ※なかよくしろよ")
st.caption(f"現在のID: `{get_trip_id()}` | [URLコピー](https://my-bbs-app.streamlit.app/)")
# --- 実際の表示部分 ---
app_url = "https://my-bbs-app-6heicw938faphfqgz4ayw5.streamlit.app" # あなたのアプリのURL
st.caption("📱 この掲示板のURL:")
st.code(app_url)

# ここでQRコードを表示！
show_qr(app_url)


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
    # --- サイドバーにスレッド一覧を表示（PCなら常に表示、スマホならメニュー内） ---
    with st.sidebar:
        st.title("🧵 スレッド一覧")
        for title, info in sorted_threads:
            if st.button(f"{title} ({info['count']})", key=f"side_{title}", use_container_width=True):
                st.session_state.current_thread = title
                st.rerun()
        
        st.divider()
        if st.button("🏠 トップに戻る", use_container_width=True):
            st.session_state.current_thread = None
            st.rerun()
    
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
    
# 1. まずスレッド内の各IDの登場回数を数える
    id_counts = {}
    for post in res.data:
        uid = post['user_id']
        id_counts[uid] = id_counts.get(uid, 0) + 1

    # 2. 投稿を表示する
    for i, post in enumerate(res.data):
        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
        time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
        
        uid = post['user_id']
        # そのIDがこれまでに何回登場したか取得
        count_num = id_counts[uid]
        
        with st.container(border=True):
            # IDの横に (回数/全レス数) を表示する2chスタイル
            st.markdown(
                f"**{i+1}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{uid} **({count_num})**", 
                unsafe_allow_html=True
            )
            st.write(post['content'])
