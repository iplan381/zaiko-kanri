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

st.set_page_config(page_title="詳細在庫分析", layout="wide")

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

st.title("📈 在庫変動 詳細分析ボード")

if not df_log_raw.empty:
    # データ前処理
    df_log = df_log_raw.copy()
    df_log["日時"] = pd.to_datetime(df_log["日時"])
    df_log["年月"] = df_log["日時"].dt.strftime("%Y-%m")
    df_log["数量"] = pd.to_numeric(df_log["数量"], errors='coerce').fillna(0)
    
    # 「商品名(サイズ/地名)」という合体した名前を作る（これでバラバラに集計できる）
    df_log["詳細項目"] = df_log["商品名"] + " (" + df_log["サイズ"] + " / " + df_log["地名"] + ")"
    
    # 出庫データのみ
    df_out = df_log[df_log["区分"].str.contains("出庫")].copy()

    # --- フィルターエリア ---
    st.sidebar.header("🔍 表示設定")
    display_type = st.sidebar.radio("表示形式", ["グラフで見たい", "表（数字）で見たい"])
    target_month = st.sidebar.multiselect("表示する月を選択", sorted(df_out["年月"].unique(), reverse=True), default=sorted(df_out["年月"].unique())[:1])

    # データの絞り込み
    df_filtered = df_out[df_out["年月"].isin(target_month)]

    if not df_filtered.empty:
        st.subheader(f"📅 選択した月の出荷状況")
        
        # 集計
        summary = df_filtered.groupby(["年月", "詳細項目"])["数量"].sum().reset_index()

        if display_type == "グラフで見たい":
            # グラフ表示
            fig = px.bar(summary, x="詳細項目", y="数量", color="年月",
                         barmode="group", text_auto=True,
                         title="詳細項目別 出荷数")
            st.plotly_chart(fig, use_container_width=True)
        else:
            # 表表示（ピボットテーブルで見やすく）
            st.write("### 🔢 出荷数一覧表")
            df_pivot = summary.pivot(index="詳細項目", columns="年月", values="数量").fillna(0)
            # 合計列を追加
            df_pivot["合計"] = df_pivot.sum(axis=1)
            st.dataframe(df_pivot.sort_values("合計", ascending=False), use_container_width=True)

        # --- 年月比較エリア（さらに詳細） ---
        st.divider()
        st.subheader("⚖️ 詳細比較（前月・前年など）")
        c1, c2 = st.columns(2)
        with c1: month_a = st.selectbox("比較A", df_out["年月"].unique(), index=0, key="a")
        with c2: month_b = st.selectbox("比較B", df_out["年月"].unique(), index=min(1, len(df_out["年月"].unique())-1), key="b")

        comp_a = df_out[df_out["年月"] == month_a].groupby("詳細項目")["数量"].sum().reset_index()
        comp_b = df_out[df_out["年月"] == month_b].groupby("詳細項目")["数量"].sum().reset_index()
        df_comp = pd.merge(comp_a, comp_b, on="詳細項目", how="outer", suffixes=(f'_{month_a}', f'_{month_b}')).fillna(0)
        
        fig_comp = px.bar(df_comp, x="詳細項目", y=[f"数量_{month_a}", f"数量_{month_b}"],
                          barmode="group", title=f"{month_a} と {month_b} の詳細比較")
        st.plotly_chart(fig_comp, use_container_width=True)

    else:
        st.info("選択された月のデータがありません。サイドバーで月を選んでください。")

else:
    st.warning("履歴データが読み込めません。")
