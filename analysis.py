import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
from io import StringIO

# --- 設定 ---
REPO_NAME = "iplan381/zaiko-kanri"
FILE_PATH_LOG = "stock_log_main.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

st.set_page_config(page_title="階層分析ダッシュボード", layout="wide")

def get_github_data(file_path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        csv_text = base64.b64decode(content["content"]).decode("utf-8")
        return pd.read_csv(StringIO(csv_text)).fillna("")
    return pd.DataFrame()

df_log_raw = get_github_data(FILE_PATH_LOG)

st.title("📈 商品・地名別の階層分析")

if not df_log_raw.empty:
    # データ前処理
    df_log = df_log_raw.copy()
    df_log["日時"] = pd.to_datetime(df_log["日時"])
    df_log["年月"] = df_log["日時"].dt.strftime("%Y-%m")
    df_log["数量"] = pd.to_numeric(df_log["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ
    df_out = df_log[df_log["区分"].str.contains("出庫")].copy()

    # --- 階層絞り込みエリア（サイドバー） ---
    st.sidebar.header("🔍 絞り込み条件")
    
    # 1. 月の選択
    month_list = sorted(df_out["年月"].unique(), reverse=True)
    sel_month = st.sidebar.selectbox("📅 ① 月を選択", month_list)
    df_m = df_out[df_out["年月"] == sel_month]

    # 2. 商品名の選択（その月に動いた商品だけ出す）
    item_list = ["すべて表示"] + sorted(df_m["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ② 商品名を選択", item_list)
    
    if sel_item != "すべて表示":
        df_i = df_m[df_m["商品名"] == sel_item]
        # 3. 地名の選択（その商品がある地名だけ出す）
        loc_list = ["すべて表示"] + sorted(df_i["地名"].unique().tolist())
        sel_loc = st.sidebar.selectbox("📍 ③ 地名を選択", loc_list)
    else:
        df_i = df_m
        sel_loc = "すべて表示"

    # 最終的な絞り込み
    if sel_loc != "すべて表示":
        df_final = df_i[df_i["地名"] == sel_loc]
        title_suffix = f"【{sel_item} / {sel_loc}】"
    elif sel_item != "すべて表示":
        df_final = df_i
        title_suffix = f"【{sel_item} (全地名)】"
    else:
        df_final = df_m
        title_suffix = "【全商品・全地名】"

    # --- 表示メインエリア ---
    tab1, tab2 = st.tabs(["📊 グラフで確認", "🔢 表（数字）で確認"])

    with tab1:
        st.subheader(f"{sel_month} の出荷状況 {title_suffix}")
        if not df_final.empty:
            # グラフ用のラベル作成
            df_final["表示名"] = df_final["商品名"] + " (" + df_final["サイズ"] + " / " + df_final["地名"] + ")"
            summary = df_final.groupby("表示名")["数量"].sum().reset_index()
            
            fig = px.bar(summary, x="表示名", y="数量", text_auto=True,
                         color="数量", color_continuous_scale="Blues")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("該当するデータがありません。")

    with tab2:
        st.subheader(f"詳細データ一覧 ({sel_month})")
        if not df_final.empty:
            # 表を見やすく整理
            view_df = df_final[["日時", "商品名", "サイズ", "地名", "区分", "数量", "担当者"]].sort_values("日時", ascending=False)
            st.dataframe(view_df, use_container_width=True, hide_index=True)
        else:
            st.info("該当するデータがありません。")

else:
    st.warning("履歴データが読み込めません。")
