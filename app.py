import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib
import qrcode
from io import BytesIO
import re
import streamlit as st
from streamlit_autorefresh import st_autorefresh # これを追加

# --- ページ設定のすぐ下あたりに追加 ---
# 5秒（5000ミリ秒）ごとに画面を自動更新する
# これを入れるだけで、誰かの投稿が5秒以内に全員の画面に反映されます！
st_autorefresh(interval=5000, key="bbs_refresh")

# (ここから下に、いつもの掲示板のコードが続く...)
# 1. 一番最初に設定を書く（1回だけ！）
st.set_page_config(
    page_title="休サイト - 究極の匿名掲示板", 
    page_icon="💬", 
    layout="centered"
)

# 2. その直後に Google の確認用タグを入れる
st.markdown('<meta name="google-site-verification" content="9z3A-fzdRLWmFx2ZNkg47ac0I99VffSQ35i9XERd7v4" />', unsafe_allow_html=True)

# 3. 接続設定など
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="休サイト", page_icon="💬", layout="centered")
# ページタイトルをしっかり設定する（これが検索結果のタイトルになります）
st.set_page_config(page_title="休サイト - 休憩の匿名掲示板", page_icon="💬")

# サイトの説明文（メタディスクリプション風）を画面上に書く
st.write("休サイトは、誰でも気軽に書き込める完全匿名の掲示板アプリです。")
# --- セッション状態の初期化（これを忘れずに！） ---
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
# --- 管理者認証システム ---
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
if st.session_state.admin_mode:
    st.header("⚙️ 投稿管理（削除モード）")
    
    # Supabaseから最新の全投稿を取得
    res = supabase.table("bbs_posts").select("*").order("created_at", desc=True).execute()
    posts = res.data

    if not posts:
        st.info("投稿はまだありません。")
    else:
        for post in posts:
            # 投稿ごとに枠を作って表示
            with st.container(border=True):
                col1, col2 = st.columns([8, 2])
                
                with col1:
                    st.write(f"**{post['name']}** - {post['created_at']}")
                    st.write(post['content'])
                
                with col2:
                    # 削除ボタン。クリックされたらSupabaseから消す
                    if st.button("削除", key=f"del_{post['id']}"):
                        supabase.table("bbs_posts").delete().eq("id", post['id']).execute()
                        st.success(f"投稿 ID:{post['id']} を削除しました")
                        st.rerun() # 画面を更新して消えたことを反映

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

# --- メイン画面の切り替え ---
if st.session_state.admin_mode:
    st.header("⚙️ 管理者専用：投稿管理")
    # ここに投稿一覧と削除ボタンを表示するコードを書く
    # 例: res = supabase.table("bbs_posts").select("*").execute() ...
else:
    # ここにいつもの掲示板コード（スレッド表示など）を書く
    pass

# 匿名ID生成
def get_trip_id():
    date_str = datetime.now().strftime("%Y-%m-%d")
    if "user_secret_key" not in st.session_state:
        import random
        import string
        st.session_state.user_secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    combined = date_str + st.session_state.user_secret_key
    return hashlib.sha256(combined.encode()).hexdigest()[:8]

# QRコード生成
def show_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf, caption="スマホで読み取って参加！", width=150)

# --- ヘッダー表示 ---
st.title("休サイト ※なかよくしてね(^ O ^)ﾉｼ)")
app_url = "https://my-bbs-app-6heicw938faphfqgz4ayw5.streamlit.app"
st.caption(f"現在のID: `{get_trip_id()}` | [URLコピー]({app_url})")
show_qr(app_url)

# --- ① スレッド情報の取得 ---
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

sorted_threads = sorted(thread_info.items(), key=lambda x: x[1]['latest'], reverse=True)

if "current_thread" not in st.session_state:
    st.session_state.current_thread = None

# --- スレッド一覧画面 ---
if st.session_state.current_thread is None:
    with st.sidebar:
        st.title("🧵 スレッド一覧")
        for title, info in sorted_threads:
            if st.button(f"{title} ({info['count']})", key=f"side_{title}", use_container_width=True):
                st.session_state.current_thread = title
                st.rerun()

    with st.expander("➕ 新しいスレッドを立てる"):
        with st.form("new_thread_form", clear_on_submit=True):
            # max_chars で入力欄そのものに制限をかける（バッファ対策）
            new_t = st.text_input("スレッド名", max_chars=50) 
            name = st.text_input("名前", placeholder="風吹けば恋さん", max_chars=20)
            msg = st.text_area("最初の書き込み", max_chars=1000) 
            
            if st.form_submit_button("スレッド作成"):
                # strip() を使うことで「スペースだけの投稿」も弾く
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
                    st.error("スレッド名と最初の書き込みを入力してください（空白のみは不可）")
    
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

     with st.expander("💬 このスレに書き込む"):
            # clear_on_submit=True を追加（念のため）
            with st.form("post_in_thread", clear_on_submit=True):
                # key を指定するのが一番のポイント！
                input_name = st.text_input("名前", placeholder="風吹けば恋さん", key="input_name_key")
                msg = st.text_area("本文", key="input_msg_key")
                
                if st.form_submit_button("書き込む"):
                    if msg.strip(): # 空白文字だけの投稿も防ぐ
                        supabase.table("bbs_posts").insert({
                            "thread_title": st.session_state.current_thread,
                            "name": input_name if input_name else "風吹けば恋さん",
                            "content": msg.strip(), 
                            "user_id": get_trip_id()
                        }).execute()
                        
                        # ✅ ここが重要！ rerun する前に state を直接空にする
                        st.session_state["input_msg_key"] = ""
                        # 名前も消したい場合は↓も追加。残したいなら書かなくてOK
                        # st.session_state["input_name_key"] = ""
                        # 2. 通知を出す（アイコンも付けられます！）
                        st.toast("書き込みが完了しました！", icon="✅")
                        st.rerun()

    # レス表示
    res = supabase.table("bbs_posts").select("*").eq("thread_title", st.session_state.current_thread).order("created_at", desc=False).execute()
    
    id_counts = {}
    for post in res.data:
        uid = post['user_id']
        id_counts[uid] = id_counts.get(uid, 0) + 1

    # ジャンプ位置の調整
    st.markdown("<style>[id^='p'] { scroll-margin-top: 100px; }</style>", unsafe_allow_html=True)

    for i, post in enumerate(res.data):
        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
        time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
        uid = post['user_id']
        content = post['content'] # ★ここなら post が存在するのでエラーにならない！

        # メンション変換関数
        def link_repl(match):
            num = match.group(1)
            return f'<a href="#p{num}" target="_self" style="color: #1e90ff; font-weight: bold; text-decoration: none;">>>{num}</a>'
        
        converted_content = re.sub(r'>>(\d+)', link_repl, content)

        with st.container(border=True):
            st.markdown(f'<div id="p{i+1}"></div>', unsafe_allow_html=True)
            st.markdown(
                f"**{i+1}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{uid} **({id_counts[uid]})**", 
                unsafe_allow_html=True
            )
            # 本文表示
            st.markdown(converted_content, unsafe_allow_html=True)
            
