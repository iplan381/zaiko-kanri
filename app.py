import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. あなたのスプレッドシートURL（正規の形）
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4/edit?usp=sharing"

# あなたが元々定義していたリスト
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# 2. 接続の確立
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. データ読み込み（エラー回避のための最小構成）
def load_data():
    try:
        # worksheet名を指定せずに、まずは一番左のシートを読み込む
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl="0s")
        return df.fillna("")
    except Exception as e:
        st.error("Google側でアクセスが拒否されました。スプレッドシートのURLが正しいか再度確認してください。")
        st.stop()

# 4. 並び替え（あいうえお順に整列）
def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

df_stock = load_data()

st.title("📦 在庫管理システム")

# メイン表示（地名をあいうえお順に）
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
if not df_stock.empty:
    with c1:
        s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
    with c2:
        s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
    with c3:
        # これで 青森→北海道→和歌山 の順になります
        s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
    with c4:
        s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

    # 絞り込み表示
    df_disp = df_stock.copy()
    if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
    if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
    if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
    if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

    st.dataframe(df_disp, use_container_width=True, hide_index=True)
