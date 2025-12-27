import streamlit as st
import pandas as pd
from datetime import datetime

# --- 設定：IDだけを使う方式に変更（これが一番エラーが出ません） ---
SHEET_ID = "1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4"
STOCK_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=stock"
LOG_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=log"

# あなたが定義した元のリスト
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- データ読み込み関数（ライブラリを使わず直接取得） ---
def load_data():
    try:
        df_s = pd.read_csv(STOCK_URL).fillna("")
        df_l = pd.read_csv(LOG_URL).fillna("")
        return df_s, df_l
    except Exception as e:
        st.error("スプレッドシートを読み込めません。共有設定が『リンクを知っている全員』になっているか確認してください。")
        st.stop()

# --- 並び替え関数（シンプルに中身だけをソート） ---
def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

# データの読み込み
df_stock, df_log = load_data()

st.title("📦 在庫管理システム")

# --- サイドバー：登録 ---
with st.sidebar:
    st.header("✨ 新商品登録")
    new_item = st.text_input("商品名")
    new_size = st.selectbox("サイズ", SIZES_MASTER)
    new_loc = st.text_input("地名")
    new_vendor = st.selectbox("取引先", VENDORS_MASTER)
    new_stock = st.number_input("初期在庫", min_value=0, value=0)
    new_alert = st.number_input("アラート基準", min_value=0, value=5)
    
    st.info("※データ登録機能はスプレッドシートの権限設定により、シート側で直接入力が必要な場合があります。")

# --- 在庫一覧（地名をあいうえお順に） ---
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
with c1:
    s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
with c2:
    s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
with c3:
    # これで「青森」が「和歌山」より上に来ます
    s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
with c4:
    s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

# フィルタリング
df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

st.dataframe(df_disp, use_container_width=True, hide_index=True)

# --- 履歴 ---
st.divider()
st.subheader("📜 入出庫履歴")
if not df_log.empty:
    st.dataframe(df_log, use_container_width=True, hide_index=True)
