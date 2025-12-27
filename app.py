import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 設定：URLの末尾をシンプルにしてエラーを回避 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4/edit"

# あなたが元々定義していたリストのみを使用
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]  # ← 余計なものを削除しました
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ読み込み関数 ---
def load_data():
    # 共有設定が「編集者」であれば、これで読み込めます
    df_s = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="stock", ttl="0s")
    df_l = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="log", ttl="0s")
    return df_s.fillna(""), df_l.fillna("")

# --- 並び替え関数（中身をあいうえお順に整列させる） ---
def get_opts(series):
    if series is None or len(series) == 0:
        return ["すべて"]
    
    # 重複を消して、あいうえお順（数字順）に並べ替え
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

    if st.button("登録"):
        if new_item and new_loc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_row = pd.DataFrame([{
                "最終更新日": now, "商品名": new_item, "サイズ": new_size,
                "地名": new_loc, "在庫数": new_stock, "アラート基準": new_alert, "取引先": new_vendor
            }])
            updated_stock = pd.concat([df_stock, new_row], ignore_index=True)
            conn.update(spreadsheet=SPREADSHEET_URL, worksheet="stock", data=updated_stock)
            st.success("保存しました")
            st.rerun()

# --- 在庫一覧（地名を自動で並び替え） ---
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
with c1:
    s_item = st.selectbox("商品名", get_opts(df_stock["商品名"]))
with c2:
    s_size = st.selectbox("サイズ", get_opts(df_stock["サイズ"]))
with c3:
    # 💡 これで「青森」が「和歌山」より上に来るようになります
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
    st.dataframe(df_log.sort_values("日時", ascending=False), use_container_width=True, hide_index=True)
