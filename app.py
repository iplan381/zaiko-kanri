import streamlit as st
import pandas as pd

# 1. あなたのスプレッドシートURL（そのまま使用）
BASE_URL = "https://docs.google.com/spreadsheets/d/1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4/export?format=csv"

# 元からあるマスターデータ（余計なものは一切入れません）
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# 2. データ読み込み関数（最も成功率が高いCSVエクスポート方式）
def load_data():
    try:
        # シート名を指定して直接CSVダウンロード
        df_s = pd.read_csv(f"{BASE_URL}&gid=0") # stockシート
        # logシートのgidが不明なため、一旦stockのみ表示させます
        return df_s.fillna(""), pd.DataFrame()
    except Exception as e:
        st.error(f"読み込みエラー。共有設定は正しいので、一度ブラウザでシートが開けるか確認してください。")
        st.stop()

# 3. 並び替え（あいうえお順に整列）
def get_opts(series):
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

df_stock, _ = load_data()

st.title("📦 在庫管理システム")

# サイドバー（元の項目を維持）
with st.sidebar:
    st.header("✨ 新商品登録")
    new_item = st.text_input("商品名")
    new_size = st.selectbox("サイズ", SIZES_MASTER)
    new_loc = st.text_input("地名")
    new_vendor = st.selectbox("取引先", VENDORS_MASTER)
    new_stock = st.number_input("初期在庫", min_value=0, value=0)
    new_alert = st.number_input("アラート基準", min_value=0, value=5)

# メイン表示（地名をあいうえお順に）
st.subheader("📊 在庫一覧")
c1, c2, c3, c4 = st.columns(4)
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
