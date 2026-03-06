import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib

# 1. 接続設定
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="匿名掲示板 休サイト", page_icon="💬", layout="centered")

# 匿名ID生成
def get_trip_id():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return hashlib.sha256(date_str.encode()).hexdigest()[:8]

# --- ヘッダー・URL表示 ---
st.caption("📱 この掲示板のURL:")
st.code("https://my-bbs-app.streamlit.app/")
# 画像がない場合のエラー回避のため、存在確認などが必要ですが一旦そのままにします
# st.image("qr_code.png", caption="スマホで読み取って参加！", width=150)

st.title("休サイト ※なかよくしろよ")

# --- ① 全投稿から話題（スレッド名）の一覧を取得 ---
res_all = supabase.table("bbs_posts").select("thread_title").execute()
# 重複を除去してリスト化
all_threads = sorted(list(set([item['thread_title'] for item in res_all.data if item['thread_title']])))
if not all_threads:
    all_threads = ["雑談"]

# --- ② サイドバーで話題を選択 ---
st.sidebar.title("🧵 話題（スレッド）")
selected_thread = st.sidebar.radio("スレッド一覧", all_threads)

# --- ③ 投稿フォーム（新しい話題も作れる） ---
with st.expander("📝 書き込む / 新しい話題を作る"):
    with st.form("bbs_post", clear_on_submit=True):
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            input_name = st.text_input("名前", placeholder="風吹けば恋さん")
            # 新しい話題を作るための入力欄
            new_thread_input = st.text_input("新しい話題を作る（空欄なら現在の話題に投稿）", placeholder="例：ラーメン、就活、ゲーム")
        with col2:
            st.write(f"ID: `{get_trip_id()}`")
            st.write(f"現在の話題: **{selected_thread}**")
            
        message = st.text_area("本文 (最大1000文字)", max_chars=1000)
        submitted = st.form_submit_button("書き込む", use_container_width=True, type="primary")
        
        if submitted and message:
            final_name = input_name if input_name else "風吹けば恋さん"
            # 新しい話題が入力されていればそれを、なければ選択中の話題を使用
            target_thread = new_thread_input.strip() if new_thread_input.strip() else selected_thread
            
            supabase.table("bbs_posts").insert({
                "name": final_name,
                "content": message,
                "user_id": get_trip_id(),
                "thread_title": target_thread
            }).execute()
            st.success(f"【{target_thread}】に書き込みました！")
            st.rerun()

st.divider()

# --- ④ 閲覧エリア（選択された話題の投稿のみ表示） ---
st.subheader(f"💬 話題：{selected_thread}")

res = supabase.table("bbs_posts").select("*").eq("thread_title", selected_thread).order("created_at", desc=True).execute()

if not res.data:
    st.info("この話題にはまだ書き込みがありません。")
else:
    for i, post in enumerate(res.data):
        post_num = len(res.data) - i
        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
        time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
        
        with st.container(border=True):
            st.markdown(f"**{post_num}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{post['user_id']}", unsafe_allow_html=True)
            st.write(post['content'])
            
