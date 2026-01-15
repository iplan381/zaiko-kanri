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

st.set_page_config(page_title="詳細階層分析", layout="wide")

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

st.title("📈 階層別 在庫動態分析")

if not df_log_raw.empty:
    # データ前処理
    df = df_log_raw.copy()
    df["日時"] = pd.to_datetime(df["日時"])
    df["年"] = df["日時"].dt.year
    df["月"] = df["日時"].dt.month
    df["数量"] = pd.to_numeric(df["数量"], errors='coerce').fillna(0)
    
    # 出庫データのみ
    df_out = df[df["区分"].str.contains("出庫")].copy()

    # --- 5段階 階層絞り込み（サイドバー） ---
    st.sidebar.header("🔍 絞り込み条件")
    
    # 1. 年
    year_list = sorted(df_out["年"].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 ① 年を選択", year_list)
    df_y = df_out[df_out["年"] == sel_year]

    # 2. 月
    # すべて表示も選べるように
    month_options = ["すべて表示"] + sorted(df_y["月"].unique().tolist())
    sel_month = st.sidebar.selectbox("📆 ② 月を選択", month_options)
    
    if sel_month != "すべて表示":
        df_m = df_y[df_y["月"] == sel_month]
    else:
        df_m = df_y

    # 3. 商品名
    item_list = ["すべて表示"] + sorted(df_m["商品名"].unique().tolist())
    sel_item = st.sidebar.selectbox("📦 ③ 商品名を選択", item_list)
    
    if sel_item != "すべて表示":
        df_i = df_m[df_m["商品名"] == sel_item]
        # 4. 地名
        loc_list = ["すべて表示"] + sorted(df_i["地名"].unique().tolist())
        sel_loc = st.sidebar.selectbox("📍 ④ 地名を選択", loc_list)
        
        if sel_loc != "すべて表示":
            df_l = df_i[df_i["地名"] == sel_loc]
            # 5. サイズ
            size_list = ["すべて表示"] + sorted(df_l["サイズ"].unique().tolist())
            sel_size = st.sidebar.selectbox("📏 ⑤ サイズを選択", size_list)
        else:
            df_l = df_i
            sel_size = "すべて表示"
    else:
        df_i = df_m
        sel_loc = "すべて表示"
        sel_size = "すべて表示"

    # 最終フィルター適用
    df_final = df_m.copy()
    title_parts = [f"{sel_year}年"]
    if sel_month != "すべて表示": title_parts.append(f"{sel_month}月")
    
    if sel_item != "すべて表示":
        df_final = df_final[df_final["商品名"] == sel_item]
        title_parts.append(sel_item)
    if sel_loc != "すべて表示":
        df_final = df_final[df_final["地名"] == sel_loc]
        title_parts.append(sel_loc)
    if sel_size != "すべて表示":
        df_final = df_final[df_final["サイズ"] == sel_size]
        title_parts.append(sel_size)

    display_title = " / ".join(title_parts)

    # --- メイン表示 ---
    tab1, tab2 = st.tabs(["📊 出荷グラフ", "🔢 詳細データ一覧"])

    with tab1:
        st.subheader(f"出荷状況: {display_title}")
        if not df_final.empty:
            # グラフ用の項目名作成
            df_final["表示項目"] = df_final["商品名"] + " (" + df_final["サイズ"] + " / " + df_final["地名"] + ")"
            # 月が「すべて表示」の場合は月別で色分け、そうでない場合は項目別で色分け
            if sel_month == "すべて表示":
                summary = df_final.groupby(["月", "表示項目"])["数量"].sum().reset_index()
                fig = px.bar(summary, x="表示項目", y="数量", color="月", text_auto=True,
                             title="月別の内訳", barmode="group")
            else:
                summary = df_final.groupby("表示項目")["数量"].sum().reset_index()
                fig = px.bar(summary, x="表示項目", y="数量", text_auto=True,
                             color="数量", color_continuous_scale="Viridis")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("該当するデータがありません。条件を広げてください。")

    with tab2:
        st.subheader("分析対象の全履歴")
        if not df_final.empty:
            st.dataframe(df_final[["日時", "商品名", "サイズ", "地名", "数量", "担当者"]].sort_values("日時", ascending=False),
                         use_container_width=True, hide_index=True)
        else:
            st.info("データがありません。")

else:
    st.warning("履歴データが読み込めません。")
