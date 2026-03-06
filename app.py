import streamlit as st
from supabase import create_client
from datetime import datetime
import pytz
import hashlib

# 1. 接続設定（既存のSecretsをそのまま使用）
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="匿名掲示板　休サイト", page_icon="💬")

# 匿名ID生成（日付ごとに変わる「今日の日付」仕様）
def get_trip_id():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return hashlib.sha256(date_str.encode()).hexdigest()[:8]

st.title("(^ o ^)ノシ 休サイト (β)")

# --- 投稿フォーム ---
with st.form("bbs_post", clear_on_submit=True):
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        # プレースホルダーで「名無しさん」を提案
        input_name = st.text_input("名前", placeholder="風吹けば恋")
    with col2:
        st.write(f"あなたのID: `{get_trip_id()}`")
        
    message = st.text_area("本文 (最大1000文字)", max_chars=1000)
    submitted = st.form_submit_button("書き込む", use_container_width=True, type="primary")
    
    if submitted and message:
        # 【重要】名前が空なら「名無しさん」にするロジック
        final_name = input_name if input_name else "名無しさん"
        
        # 新しく作った「bbs_posts」テーブルにインサート！
        supabase.table("bbs_posts").insert({
            "name": final_name,
            "content": message,
            "user_id": get_trip_id()
        }).execute()
        st.success("書き込みに成功しました！")
        st.rerun()

st.divider()

# --- 閲覧エリア（2ch風のデザイン演出） ---
# 最新の投稿から順に取得
res = supabase.table("bbs_posts").select("*").order("created_at", desc=True).execute()

if not res.data:
    st.info("まだ書き込みがありません。最初の1人になりませんか？")
else:
    for i, post in enumerate(res.data):
        # 投稿番号（全件数から逆算）
        post_num = len(res.data) - i
        # 日本時間に変換
        dt = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Tokyo'))
        time_str = dt.strftime('%Y/%m/%d %H:%M:%S')
        
        # 枠線で囲って掲示板っぽく表示
        with st.container(border=True):
            # ヘッダー：番号、名前（緑色）、日時、ID
            st.markdown(f"**{post_num}** ：<font color='#117711'>**{post['name']}**</font> ：{time_str} ID:{post['user_id']}", unsafe_allow_html=True)
            # 本文
            st.write(post['content'])
